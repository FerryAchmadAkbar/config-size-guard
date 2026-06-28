"""
src/csg/reporter/text.py — Trace Output Reporter
"""
import click
from ..models import FileResult

class TextReporter:
    def print_report(self, results: list[FileResult], verbose: bool, env: str = 'local'):
        click.secho("\n" + "="*60, fg="cyan")
        click.secho(" 🛡️  Config Size Guard - Behavioral Trace Report", fg="cyan", bold=True)
        click.secho("="*60 + "\n", fg="cyan")

        pass_count = 0
        warn_count = 0
        crit_count = 0

        for res in results:
            if res.verdict == "CRITICAL":
                crit_count += 1
                color = "red"
                icon = "❌"
            elif res.verdict == "WARN":
                warn_count += 1
                color = "yellow"
                icon = "⚠️"
            else:
                pass_count += 1
                color = "green"
                icon = "✅"

            # Jika mode tidak verbose, sembunyikan file yang PASS
            if res.verdict == "PASS" and not verbose:
                continue

            # Cetak Header File
            click.secho(f"{icon} [{res.verdict}] {res.filepath}", fg=color, bold=True)

            # Cetak Trace Output dari setiap Analyzer
            for check in res.checks:
                click.secho(f"   [{check.check.upper()}]", fg="blue")
                if check.detail:
                    click.secho(f"   detail={check.detail}", fg="white")
                click.secho(f"   score={check.score}", fg="white")
                click.echo("")

            # Cetak Correlation Boost (Jika ada)
            if res.correlations_triggered:
                click.secho("   [CORRELATION]", fg="magenta", bold=True)
                for corr in res.correlations_triggered:
                    click.secho(f"   {corr}", fg="magenta")
                click.echo("")

            # Cetak Final Score & Verdict
            click.secho("   [TOTAL]", fg="cyan", bold=True)
            click.secho(f"   {res.total_score} => {res.verdict}\n", fg=color, bold=True)

            # GitHub Actions Annotations (Jika di mode CI)
            if env == 'ci' and res.verdict in ["WARN", "CRITICAL"]:
                level = "error" if res.verdict == "CRITICAL" else "warning"
                click.echo(f"::{level} file={res.filepath},title=CSG_V4_Violation::Total Score: {res.total_score}. Correlations: {', '.join(res.correlations_triggered)}")

        # Cetak Ringkasan Akhir
        click.secho("-" * 60, fg="cyan")
        click.echo(f"Total File Diperiksa : {len(results)}")
        click.secho(f" ✅ PASS             : {pass_count}", fg="green")
        click.secho(f" ⚠️ WARN             : {warn_count}", fg="yellow")
        click.secho(f" ❌ CRITICAL         : {crit_count}", fg="red")