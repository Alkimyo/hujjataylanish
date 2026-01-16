from django.core.management.base import BaseCommand
from documents.models import SecurityPolicy


class Command(BaseCommand):
    help = "Generate portscan fail2ban/nftables configs from SecurityPolicy"

    def add_arguments(self, parser):
        parser.add_argument(
            "--write",
            action="store_true",
            help="Write to system paths (requires sudo)",
        )
        parser.add_argument(
            "--nft-output",
            default="/etc/nftables.d/portscan.nft",
            help="nftables output path",
        )
        parser.add_argument(
            "--filter-output",
            default="/etc/fail2ban/filter.d/portscan.conf",
            help="fail2ban filter output path",
        )
        parser.add_argument(
            "--jail-output",
            default="/etc/fail2ban/jail.d/portscan.local",
            help="fail2ban jail output path",
        )

    def handle(self, *args, **options):
        policy = SecurityPolicy.objects.order_by("-updated_at").first()
        if not policy:
            policy = SecurityPolicy.objects.create()

        rate = policy.rate_limit_per_minute
        burst = policy.burst
        findtime = policy.findtime_seconds
        maxretry = policy.maxretry
        bantime = policy.bantime_seconds
        ignoreip = policy.get_ignoreip_value()

        nftables_conf = (
            "table inet portscan {\n"
            "  chain input {\n"
            "    type filter hook input priority 0; policy accept;\n"
            "    iif \"lo\" accept\n"
            "    ct state established,related accept\n"
            f"    meter scan {{ ip saddr limit rate over {rate}/minute burst {burst} packets }} \\\n"
            "      tcp flags syn ct state new \\\n"
            "      log prefix \"PORTSCAN \" level warning\n"
            "  }\n"
            "}\n"
        )

        filter_conf = (
            "[Definition]\n"
            "failregex = ^.*PORTSCAN.*SRC=<HOST>.*$\n"
            "ignoreregex =\n"
        )

        jail_conf_lines = [
            "[portscan]",
            "enabled = true",
            "filter = portscan",
            "maxretry = %s" % maxretry,
            "findtime = %s" % findtime,
            "bantime = %s" % bantime,
            "banaction = auto",
        ]
        if ignoreip:
            jail_conf_lines.append("ignoreip = %s" % ignoreip)
        jail_conf = "\n".join(jail_conf_lines) + "\n"

        if options["write"]:
            self._write_file(options["nft-output"], nftables_conf)
            self._write_file(options["filter-output"], filter_conf)
            self._write_file(options["jail-output"], jail_conf)
            self.stdout.write(self.style.SUCCESS("Config files written."))
            return

        self.stdout.write("=== nftables ===")
        self.stdout.write(nftables_conf)
        self.stdout.write("=== fail2ban filter ===")
        self.stdout.write(filter_conf)
        self.stdout.write("=== fail2ban jail ===")
        self.stdout.write(jail_conf)

    def _write_file(self, path, content):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
