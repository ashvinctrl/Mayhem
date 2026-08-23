"""Network fault injection utilities using tc netem and iptables (Linux/Docker)."""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def get_primary_interface():
    """Detect the primary outbound network interface."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "dev" in result.stdout:
            parts = result.stdout.split()
            return parts[parts.index("dev") + 1]
    except (FileNotFoundError, subprocess.TimeoutExpired, (IndexError, ValueError)):
        pass
    return "eth0"


def apply_network_latency(iface, delay_ms, jitter_ms=10):
    """
    Apply network latency via tc netem. Linux/Docker only.
    Returns (success: bool, message: str).
    """
    if os.name == "nt":
        return (
            False,
            "tc netem unavailable on Windows — run inside Docker/Linux for real injection",
        )
    try:
        # Remove any pre-existing root qdisc first (ignore errors)
        subprocess.run(
            ["tc", "qdisc", "del", "dev", iface, "root"], capture_output=True, timeout=5
        )
        result = subprocess.run(
            [
                "tc",
                "qdisc",
                "add",
                "dev",
                iface,
                "root",
                "netem",
                "delay",
                f"{delay_ms}ms",
                f"{jitter_ms}ms",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return (
                True,
                f"Applied {delay_ms}ms latency (±{jitter_ms}ms jitter) on {iface}",
            )
        return False, f"tc netem failed: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, "tc command not found — install iproute2 inside the container"
    except Exception as e:
        return False, str(e)


def remove_network_latency(iface):
    """Remove tc netem rules from interface."""
    if os.name == "nt":
        return
    try:
        subprocess.run(
            ["tc", "qdisc", "del", "dev", iface, "root"], capture_output=True, timeout=5
        )
        logger.debug(f"Removed tc netem from {iface}")
    except Exception as e:
        logger.warning(f"Failed to remove tc netem from {iface}: {e}")


def apply_packet_loss(iface, loss_pct):
    """Apply packet loss via tc netem. Returns (success, message)."""
    if os.name == "nt":
        return False, "Not available on Windows"
    try:
        subprocess.run(
            ["tc", "qdisc", "del", "dev", iface, "root"], capture_output=True, timeout=5
        )
        result = subprocess.run(
            [
                "tc",
                "qdisc",
                "add",
                "dev",
                iface,
                "root",
                "netem",
                "loss",
                f"{loss_pct}%",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, f"Applied {loss_pct}% packet loss on {iface}"
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, "tc not found"
    except Exception as e:
        return False, str(e)


def apply_network_partition(target_host=None):
    """
    Block traffic via iptables. Linux/Docker only.
    Returns (success, undo_rules, message).
    """
    if os.name == "nt":
        return False, [], "iptables unavailable on Windows — run inside Docker/Linux"
    applied_rules = []
    try:
        if target_host:
            cmd = ["iptables", "-I", "OUTPUT", "1", "-d", target_host, "-j", "DROP"]
            undo = ["iptables", "-D", "OUTPUT", "-d", target_host, "-j", "DROP"]
        else:
            # Block all non-loopback outbound traffic
            cmd = ["iptables", "-I", "OUTPUT", "1", "!", "-o", "lo", "-j", "DROP"]
            undo = ["iptables", "-D", "OUTPUT", "!", "-o", "lo", "-j", "DROP"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            applied_rules.append(undo)
            return (
                True,
                applied_rules,
                f"Partition applied (target: {target_host or 'all external'})",
            )
        return False, [], f"iptables failed: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, [], "iptables not found — needs root + Linux"
    except Exception as e:
        return False, [], str(e)


def remove_network_partition(undo_rules):
    """Remove iptables partition rules."""
    for undo in undo_rules:
        try:
            subprocess.run(undo, capture_output=True, timeout=5)
            logger.debug(f"Removed iptables rule: {' '.join(undo)}")
        except Exception as e:
            logger.warning(f"Failed to remove iptables rule: {e}")
