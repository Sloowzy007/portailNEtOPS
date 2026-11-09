"""Controles de supervision : ICMP, DNS, port TCP.

Chaque fonction check_* renvoie un dict :
    {"result": "success" | "failure", "response_time_ms": float | None, "message": str}
run_check() execute un controle sur un equipement et l'enregistre dans la table checks.
"""
import ipaddress
import re
import socket
import subprocess
import time

from .extensions import db
from .models import Check

TIMEOUT = 3  # secondes

_PING_TIME = re.compile(r"time[=<]([\d.]+)\s*ms")


def _result(ok, elapsed_ms, message):
    return {
        "result": "success" if ok else "failure",
        "response_time_ms": round(elapsed_ms, 2) if elapsed_ms is not None else None,
        "message": message,
    }


def check_icmp(ip, timeout=TIMEOUT):
    """Ping unique vers une adresse IP (validee pour eviter toute injection)."""
    try:
        ip = str(ipaddress.ip_address(str(ip)))
    except ValueError:
        return _result(False, None, f"Adresse IP invalide : {ip}")

    start = time.perf_counter()
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), ip],
            capture_output=True, text=True, timeout=timeout + 2,
        )
    except FileNotFoundError:
        return _result(False, None, "Commande ping introuvable sur le serveur")
    except subprocess.TimeoutExpired:
        return _result(False, None, "Delai depasse")
    elapsed = (time.perf_counter() - start) * 1000

    if proc.returncode == 0:
        match = _PING_TIME.search(proc.stdout)
        rtt = float(match.group(1)) if match else elapsed
        return _result(True, rtt, "Reponse ICMP recue")
    return _result(False, None, "Pas de reponse ICMP")


def check_dns(hostname, expected_ip=None):
    """Resolution DNS du nom d'hote ; indique si l'IP attendue fait partie des reponses."""
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        return _result(False, None, f"Resolution impossible : {exc.strerror or exc}")
    elapsed = (time.perf_counter() - start) * 1000

    ips = sorted({info[4][0] for info in infos})
    message = "Resolu en : " + ", ".join(ips)
    if expected_ip is not None and str(expected_ip) not in ips:
        message += f" (different de l'IP enregistree {expected_ip})"
    return _result(True, elapsed, message)


def check_tcp(ip, port, timeout=TIMEOUT):
    """Tente une connexion TCP sur ip:port."""
    if not isinstance(port, int) or not 1 <= port <= 65535:
        return _result(False, None, f"Port invalide : {port}")

    start = time.perf_counter()
    try:
        with socket.create_connection((str(ip), port), timeout=timeout):
            pass
    except socket.timeout:
        return _result(False, None, f"Delai depasse sur le port {port}")
    except OSError as exc:
        return _result(False, None, f"Port {port} ferme ou inaccessible ({exc.strerror or exc})")
    elapsed = (time.perf_counter() - start) * 1000
    return _result(True, elapsed, f"Port {port} ouvert")


def run_check(device, check_type, port=None, user=None):
    """Execute un controle sur un equipement et enregistre le resultat.

    user=None signifie controle automatique.
    """
    if check_type == "icmp":
        outcome = check_icmp(device.ip_address)
    elif check_type == "dns":
        outcome = check_dns(device.hostname, expected_ip=device.ip_address)
    elif check_type == "tcp":
        if port is None:
            raise ValueError("Le port est obligatoire pour un controle TCP")
        outcome = check_tcp(device.ip_address, port)
    else:
        raise ValueError(f"Type de controle inconnu : {check_type}")

    check = Check(
        device_id=device.id,
        check_type=check_type,
        port=port if check_type == "tcp" else None,
        user_id=user.id if user else None,
        **outcome,
    )
    db.session.add(check)
    db.session.commit()
    return check
