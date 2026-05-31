#!/usr/bin/env python3
"""Mayhem CLI — inject chaos, check status, analyze logs, and schedule experiments."""
import click
import requests
import json
import os
import sys

BASE_URL = os.getenv("MAYHEM_URL", "http://localhost:5000")
API_KEY = os.getenv("CHAOS_API_KEY", "chaos_api_key_2025")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

SCENARIOS = [
    "cpu_spike", "memory_leak", "disk_fill", "network_latency",
    "network_partition", "process_kill", "container_restart",
    "database_slowdown", "api_timeout", "dns_failure",
    "ssl_certificate_expired", "storage_corruption",
    "kubernetes_pod_eviction", "service_discovery_failure", "load_balancer_failure",
]


def _req(method, path, **kwargs):
    try:
        return requests.request(method, f"{BASE_URL}{path}", headers=HEADERS, timeout=30, **kwargs)
    except requests.ConnectionError:
        click.echo(click.style(f"Cannot connect to Mayhem at {BASE_URL}. Is it running?", fg="red"), err=True)
        click.echo(f"  Set MAYHEM_URL env var to point to your instance.", err=True)
        sys.exit(1)


def _print_json(data):
    click.echo(json.dumps(data, indent=2, default=str))


@click.group()
@click.version_option("1.0.0")
def cli():
    """Mayhem — AI-Driven Chaos Engineering Platform

    \b
    Environment variables:
      MAYHEM_URL       Base URL  (default: http://localhost:5000)
      CHAOS_API_KEY    API key   (default: chaos_api_key_2025)
    """


@cli.command()
@click.argument("scenario", type=click.Choice(SCENARIOS, case_sensitive=False))
@click.option("--duration", "-d", default=10, show_default=True,
              help="Duration in seconds (1–300)")
@click.option("--intensity", "-i", default="medium", show_default=True,
              type=click.Choice(["low", "medium", "high"]),
              help="Chaos intensity level")
@click.option("--dry-run", is_flag=True,
              help="Preview what would happen without executing any chaos")
@click.option("--target-process", metavar="NAME",
              help="Process name to suspend/kill  [process_kill]")
@click.option("--target-container", metavar="NAME",
              help="Docker container name to restart  [container_restart]")
@click.option("--target-host", metavar="HOST",
              help="Host/IP to partition traffic to  [network_partition]")
def inject(scenario, duration, intensity, dry_run, target_process, target_container, target_host):
    """Inject a chaos scenario into the system.

    \b
    Examples:
      mayhem inject cpu_spike --duration 30 --intensity high
      mayhem inject network_latency --intensity medium --dry-run
      mayhem inject process_kill --target-process nginx
      mayhem inject container_restart --target-container my-api
      mayhem inject network_partition --target-host 10.0.0.5
    """
    payload = {
        "scenario": scenario,
        "duration": duration,
        "intensity": intensity,
        "dry_run": dry_run,
    }
    if target_process:
        payload["target_process"] = target_process
    if target_container:
        payload["target_container"] = target_container
    if target_host:
        payload["target_host"] = target_host

    if dry_run:
        click.echo(click.style(f"[DRY RUN] Previewing: {scenario} ({intensity}) for {duration}s", fg="yellow"))
    else:
        click.echo(f"Injecting {click.style(scenario, bold=True)} ({intensity}) for {duration}s…")

    resp = _req("POST", "/inject", json=payload)
    data = resp.json()

    if resp.status_code == 200:
        if dry_run:
            click.echo(click.style("No chaos was injected.", fg="yellow"))
            click.echo(f"  Impact:       {data.get('estimated_impact', '?')}")
            if data.get("requirements"):
                click.echo(f"  Requirements: {data['requirements']}")
        else:
            click.echo(click.style("Chaos injected!", fg="green"))
            click.echo(f"  {data.get('result', '')}")
            if data.get("method"):
                click.echo(f"  Method: {data['method']}")
    else:
        click.echo(click.style(f"Error ({resp.status_code}): {data.get('error', 'unknown')}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def scenarios(as_json):
    """List all available chaos scenarios."""
    resp = _req("GET", "/scenarios")
    data = resp.json()
    if as_json:
        _print_json(data)
        return
    scenarios_list = data.get("scenarios", [])
    real_count = data.get("real_count", 0)
    click.echo(f"Available scenarios ({real_count}/{len(scenarios_list)} with real injection):\n")
    for s in scenarios_list:
        tag = click.style("real", fg="green") if s.get("real") else click.style("sim ", fg="yellow")
        click.echo(f"  [{tag}] {s['name']:<30} {s.get('description', '')}")


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def status(as_json):
    """Show current system status and running experiments."""
    resp = _req("GET", "/system-status")
    data = resp.json()
    if as_json:
        _print_json(data)
        return
    cpu = data.get("cpu", {})
    mem = data.get("memory", {})
    disk = data.get("disk", {})
    procs = data.get("processes", {})
    uptime_s = data.get("uptime", 0)

    def _bar(pct, width=20):
        filled = int(pct / 100 * width)
        color = "green" if pct < 70 else "yellow" if pct < 90 else "red"
        return click.style("█" * filled + "░" * (width - filled), fg=color)

    click.echo("\n  System Status\n  " + "─" * 40)
    click.echo(f"  CPU      {_bar(cpu.get('usage_percent', 0))} {cpu.get('usage_percent', 0):.1f}%  ({cpu.get('count', '?')} cores)")
    click.echo(f"  Memory   {_bar(mem.get('percent', 0))} {mem.get('percent', 0):.1f}%")
    click.echo(f"  Disk     {_bar(disk.get('percent', 0))} {disk.get('percent', 0):.1f}%")
    click.echo(f"  Uptime   {int(uptime_s // 3600)}h {int((uptime_s % 3600) // 60)}m")
    active = procs.get('active_chaos_experiments', 0)
    if active:
        click.echo(f"  {click.style(f'Active chaos experiments: {active}', fg='yellow')}")


@cli.command()
@click.option("--limit", "-n", default=10, show_default=True, help="Number of entries")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def history(limit, as_json):
    """Show chaos experiment history."""
    resp = _req("GET", "/chaos-history")
    data = resp.json()
    if as_json:
        _print_json(data)
        return
    experiments = data.get("history", [])[:limit]
    if not experiments:
        click.echo("No experiments recorded yet.")
        return
    click.echo(f"\n  Last {len(experiments)} experiments\n  " + "─" * 50)
    for exp in experiments:
        s = exp.get("status", "?")
        color = {"completed": "green", "failed": "red", "running": "yellow", "stopped": "cyan"}.get(s, "white")
        ts = (exp.get("start_time") or "")[:19]
        impact = f"  impact={exp.get('impact_score', '?')}" if exp.get('impact_score') is not None else ""
        click.echo(
            f"  [{click.style(f'{s:<9}', fg=color)}] "
            f"{exp['scenario']:<25} {exp['intensity']:<6} {exp['duration']:>3}s"
            f"{impact}  {ts}"
        )


@cli.command()
@click.argument("logs_file", type=click.File("r"))
def analyze(logs_file):
    """Analyze a log file for failure patterns and chaos recommendations.

    \b
    Example:
      mayhem analyze /var/log/app.log
      cat app.log | mayhem analyze -
    """
    logs_text = logs_file.read()
    click.echo(f"Analyzing {len(logs_text):,} characters of logs…")

    resp = _req("POST", "/analyze-logs", json={"logs": logs_text})
    data = resp.json()

    if resp.status_code != 200:
        click.echo(click.style(f"Error: {data.get('error')}", fg="red"), err=True)
        if data.get("note"):
            click.echo(click.style(f"\nNote: {data['note']}", fg="yellow"))
        sys.exit(1)

    analysis = data.get("analysis", {})
    patterns = data.get("patterns", [])

    click.echo(f"\n  Lines:         {analysis.get('total_lines', '?')}")
    click.echo(f"  Anomaly score: {analysis.get('anomaly_score', 0):.2f}/1.0")
    ts = analysis.get("timestamp_range", {})
    if ts.get("start") != "unknown":
        click.echo(f"  Time range:    {ts.get('start')} → {ts.get('end')}")

    severity = analysis.get("severity_distribution", {})
    if severity:
        click.echo("\n  Severity breakdown:")
        for level, count in sorted(severity.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"    {level:<10} {count}")

    recs = analysis.get("recommendations", [])
    if recs:
        click.echo("\n  Recommendations:")
        for r in recs:
            click.echo(f"    {click.style('→', fg='cyan')} {r}")

    if patterns:
        click.echo(f"\n  Detected patterns ({len(patterns)}):")
        for p in patterns:
            sev = p.get("severity", "?")
            color = {"high": "red", "medium": "yellow", "low": "green"}.get(sev, "white")
            click.echo(f"    [{click.style(sev, fg=color)}] {p.get('description', '')}")
            if p.get("recommended_chaos_scenarios"):
                click.echo(f"           → Test with: {click.style(', '.join(p['recommended_chaos_scenarios']), fg='cyan')}")


@cli.command()
@click.option("--json", "as_json", is_flag=True)
def predict(as_json):
    """Predict failure risk from current system metrics."""
    resp = _req("GET", "/predict")
    data = resp.json()
    if as_json:
        _print_json(data)
        return
    risk = data.get("overall_risk", "?")
    score = data.get("risk_score", 0)
    color = {"high": "red", "medium": "yellow", "low": "green"}.get(risk, "white")
    click.echo(f"\n  Risk: {click.style(risk.upper(), fg=color, bold=True)}  (score: {score:.2f})\n")
    for k, v in data.get("specific_risks", {}).items():
        bar_color = "green" if v < 0.4 else "yellow" if v < 0.7 else "red"
        click.echo(f"  {k:<20} {click.style(f'{v:.2f}', fg=bar_color)}")
    recs = data.get("recommended_preventive_chaos", [])
    if recs:
        click.echo(f"\n  Recommended preventive tests: {click.style(', '.join(recs), fg='cyan')}")


@cli.command("get")
@click.argument("experiment_id", type=int)
def get_experiment(experiment_id):
    """Get details of a specific experiment by ID."""
    resp = _req("GET", f"/experiments/{experiment_id}")
    if resp.status_code == 404:
        click.echo(f"Experiment {experiment_id} not found.", err=True)
        sys.exit(1)
    _print_json(resp.json())


@cli.command("stop")
@click.argument("experiment_id", type=int)
def stop_experiment(experiment_id):
    """Stop a running chaos experiment."""
    resp = _req("POST", f"/experiments/{experiment_id}/stop")
    data = resp.json()
    if resp.status_code == 200:
        click.echo(click.style(data.get("message", "Stopped"), fg="green"))
    else:
        click.echo(click.style(f"Error: {data.get('error')}", fg="red"), err=True)
        sys.exit(1)


@cli.command("schedule")
@click.argument("scenario", type=click.Choice(SCENARIOS, case_sensitive=False))
@click.option("--at", "run_at", required=True,
              help="ISO datetime to fire (e.g. 2026-06-01T14:00:00)")
@click.option("--duration", "-d", default=10, show_default=True)
@click.option("--intensity", "-i", default="medium", show_default=True,
              type=click.Choice(["low", "medium", "high"]))
def schedule_cmd(scenario, run_at, duration, intensity):
    """Schedule a chaos experiment to run at a specific time.

    \b
    Example:
      mayhem schedule cpu_spike --at 2026-06-01T02:00:00 --intensity high
    """
    payload = {"scenario": scenario, "run_at": run_at, "duration": duration, "intensity": intensity}
    resp = _req("POST", "/schedule", json=payload)
    data = resp.json()
    if resp.status_code == 200:
        click.echo(click.style(f"Scheduled: {data.get('job_id')}", fg="green"))
        click.echo(f"  Runs at:   {data.get('run_at')}")
        click.echo(f"  Scenario:  {data.get('scenario')} ({data.get('intensity')}) for {data.get('duration')}s")
    else:
        click.echo(click.style(f"Error: {data.get('error')}", fg="red"), err=True)
        sys.exit(1)


@cli.command("schedules")
def list_schedules():
    """List all pending scheduled chaos experiments."""
    resp = _req("GET", "/schedules")
    data = resp.json()
    jobs = data.get("schedules", [])
    if not jobs:
        click.echo("No scheduled experiments.")
        return
    click.echo(f"\n  Scheduled experiments ({len(jobs)}):\n")
    for job in jobs:
        click.echo(f"  [{job['id']}]  {job.get('scenario', '?'):<25} at {job.get('run_at', '?')}")


@cli.command("cancel")
@click.argument("job_id")
def cancel_schedule(job_id):
    """Cancel a scheduled experiment by job ID."""
    resp = _req("DELETE", f"/schedules/{job_id}")
    data = resp.json()
    if resp.status_code == 200:
        click.echo(click.style(data.get("message", "Cancelled"), fg="green"))
    else:
        click.echo(click.style(f"Error: {data.get('error')}", fg="red"), err=True)


@cli.command()
def health():
    """Check if Mayhem is running and reachable."""
    resp = _req("GET", "/health")
    data = resp.json()
    click.echo(f"  {click.style(data.get('status', '?'), fg='green')}")
    running = data.get("running_experiments", 0)
    if running:
        click.echo(f"  Active experiments: {running}")


if __name__ == "__main__":
    cli()
