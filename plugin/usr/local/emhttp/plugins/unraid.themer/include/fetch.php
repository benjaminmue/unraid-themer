<?php
/* Downloading what the user points the plugin at: theme CSS, icon SVGs,
 * background and logo images, the theme store.
 *
 * The download runs on the server, inside the LAN, so a URL must never reach
 * anything a browser on the internet could not: not the server itself, the
 * router, other LAN or Tailscale hosts, or a cloud metadata address. Every URL
 * is https on port 443, its host name must resolve only to public addresses
 * outside the server's own networks,
 * and curl is pinned to the address that was checked (--resolve), so a DNS
 * answer that changes between check and connect does not matter; the address
 * curl actually connected to is compared afterwards as well. Redirects
 * are followed here, one hop at a time, with the same check on every hop.
 *
 * Not covered: the router's own public address. Through hairpin NAT it can
 * forward to a LAN service, but only what its port forwards already expose
 * to the internet, and a download only ever lands on this server as an image
 * or stylesheet, never back with whoever supplied the URL. Finding that
 * address would need an outside lookup service.
 *
 * test/test_fetch_rules.py runs the checks against private ranges, encoded
 * addresses and URL tricks. */

const THEMER_FETCH_HOPS = 5;

// Ranges PHP's FILTER_FLAG_NO_PRIV_RANGE / NO_RES_RANGE do not all cover:
// shared address space (CGNAT, Tailscale), IETF and benchmark ranges,
// IPv4-mapped/-translated IPv6, 6to4, Teredo, multicast, documentation.
function themer_ip_blocked_ranges() {
    return ['0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8', '169.254.0.0/16',
            '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24', '192.88.99.0/24', '192.168.0.0/16',
            '198.18.0.0/15', '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/3',
            '::/96', '::ffff:0:0/96', '64:ff9b::/96', '64:ff9b:1::/48', '100::/64',
            '2001::/32', '2001:db8::/32', '2002::/16', 'fc00::/7', 'fe80::/10', 'fec0::/10',
            'ff00::/8'];
}

function themer_ip_in_cidr($ip, $cidr) {
    [$net, $bits] = explode('/', $cidr);
    $a = @inet_pton($ip);
    $b = @inet_pton($net);
    if ($a === false || $b === false || strlen($a) !== strlen($b)) return false;
    $bits = (int) $bits;
    $bytes = intdiv($bits, 8);
    if (substr($a, 0, $bytes) !== substr($b, 0, $bytes)) return false;
    if ($bits % 8 === 0) return true;
    $mask = 0xff << (8 - $bits % 8) & 0xff;
    return (ord($a[$bytes]) & $mask) === (ord($b[$bytes]) & $mask);
}

// true only for an address a host on the internet could also reach
function themer_ip_public($ip) {
    if (filter_var($ip, FILTER_VALIDATE_IP,
            FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) return false;
    foreach (themer_ip_blocked_ranges() as $cidr) {
        if (themer_ip_in_cidr($ip, $cidr)) return false;
    }
    return true;
}

// The networks this server sits in, from its interface addresses ("ip -o
// addr"): the connected prefix of each, and for a global IPv6 address the
// whole /48 around it, since an ISP delegates one prefix for all VLANs of a
// site and those hosts carry public-looking addresses too. null when the
// interfaces cannot be read, which refuses every download. $text replaces
// the command in tests.
function themer_local_prefixes($text = null) {
    static $cache = null;
    $live = $text === null;
    if ($live) {
        if ($cache !== null) return $cache;
        $ip = is_executable('/sbin/ip') ? '/sbin/ip' : 'ip';
        $text = (string) shell_exec("$ip -o addr show 2>/dev/null");
    }
    preg_match_all('#\binet6?\s+([0-9a-f.:]+)/(\d+)#i', $text, $m, PREG_SET_ORDER);
    if (!$m) return null;
    $out = [];
    foreach ($m as [, $addr, $len]) {
        $len = (int) $len;
        if (strpos($addr, ':') !== false) $len = min($len, 48);
        $out[] = "$addr/$len";
    }
    if ($live) $cache = $out;
    return $out;
}

// Every address a host name resolves to, through DNS and the system resolver
// (which also reads /etc/hosts). $resolver replaces both in tests.
function themer_resolve_host($host, $resolver = null) {
    if ($resolver) return $resolver($host);
    $ips = [];
    foreach (@dns_get_record($host, DNS_A | DNS_AAAA) ?: [] as $r) {
        if (isset($r['ip'])) $ips[] = $r['ip'];
        if (isset($r['ipv6'])) $ips[] = $r['ipv6'];
    }
    foreach (@gethostbynamel($host) ?: [] as $ip) $ips[] = $ip;
    return array_values(array_unique($ips));
}

// Check one URL: [host, addresses curl may connect to, error]. $resolver and $local
// (interface list as "ip -o addr" prints it) replace the system in tests.
function themer_url_target($url, $resolver = null, $local = null) {
    if (!preg_match('#^https://[^\s\'"<>\\\\]+$#i', $url)) return ['', '', 'only https:// URLs can be used'];
    $p = parse_url($url);
    if (!$p || strtolower($p['scheme'] ?? '') !== 'https' || empty($p['host']))
        return ['', '', 'not a valid https:// URL'];
    if (isset($p['user']) || isset($p['pass'])) return ['', '', 'URLs with a user name are not accepted'];
    if (isset($p['port']) && (int) $p['port'] !== 443) return ['', '', 'only the standard https port (443) can be used'];
    // a trailing dot names the same host but would not match curl's pin
    if (substr($p['host'], -1) === '.') return ['', '', 'not a valid host name'];
    $host = strtolower($p['host']);
    $literal = trim($host, '[]');
    if (filter_var($literal, FILTER_VALIDATE_IP)) {
        $ips = [$literal];
    } else {
        // a top-level label of digits (2130706433, 0x7f.1, 127.1) makes the
        // name an address in disguise; the resolver would read it as one
        $labels = explode('.', $host);
        if (!preg_match('/^[a-z0-9.-]+$/', $host) || !preg_match('/^[a-z][a-z0-9-]*$/', end($labels)))
            return ['', '', 'not a valid host name'];
        $ips = themer_resolve_host($host, $resolver);
    }
    if (!$ips) return ['', '', "cannot resolve $host"];
    $nets = themer_local_prefixes($local);
    if ($nets === null) return ['', '', "cannot read this server's network addresses"];
    foreach ($ips as $ip) {
        if (!themer_ip_public($ip)) return ['', '', 'that address is on a private or local network'];
        foreach ($nets as $cidr) {
            if (themer_ip_in_cidr($ip, $cidr)) return ['', '', "that address is in this server's own network"];
        }
    }
    return [$host, $ips, ''];
}

// Download a URL: [body, error]. At most $max bytes; redirects are followed
// only to URLs that pass the same check.
function themer_fetch($url, $max, $timeout = 20) {
    for ($hop = 0; $hop <= THEMER_FETCH_HOPS; $hop++) {
        [$host, $ips, $err] = themer_url_target($url);
        if ($err) return ['', $err];
        // an address in the URL needs no lookup (curl refuses a pin for an
        // IPv6 literal); a name is pinned to the checked address
        $literal = filter_var(trim($host, '[]'), FILTER_VALIDATE_IP) !== false;
        // every checked address, so curl can still fall back between them
        $pin = implode(',', array_map(fn($a) => strpos($a, ':') !== false ? "[$a]" : $a, $ips));
        $tmp = tempnam(sys_get_temp_dir(), 'themer-');
        $cmd = 'curl -sS --proto =https --max-redirs 0 --noproxy ' . escapeshellarg('*')
             . ' --connect-timeout 6 --max-time ' . (int) $timeout . ' --max-filesize ' . (int) $max
             . ($literal ? '' : ' --resolve ' . escapeshellarg("$host:443:$pin"))
             . ' -o ' . escapeshellarg($tmp) . ' -w ' . escapeshellarg('%{http_code} %{remote_ip} %{redirect_url}')
             . ' ' . escapeshellarg($url) . ' 2>/dev/null';
        $out = [];
        exec($cmd, $out, $rc);
        $body = (string) @file_get_contents($tmp, false, null, 0, $max + 1);
        @unlink($tmp);
        [$code, $peer, $next] = array_pad(explode(' ', trim(implode('', $out)), 3), 3, '');
        $code = (int) $code;
        // a transfer that broke off after the headers is not a download
        if ($rc !== 0) return ['', 'could not download that URL'];
        // the pin must have held: connected to the checked address, nothing else
        $peer_bin = @inet_pton($peer);
        if ($peer_bin === false || !in_array($peer_bin, array_map('inet_pton', $ips), true))
            return ['', 'could not download that URL'];
        if ($code >= 300 && $code < 400 && $next !== '') { $url = $next; continue; }
        if ($code !== 200) return ['', $code ? "the server answered HTTP $code" : 'could not download that URL'];
        if (strlen($body) > $max) return ['', 'download too large'];
        return [$body, ''];
    }
    return ['', 'too many redirects'];
}
