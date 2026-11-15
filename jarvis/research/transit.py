"""Consultar viagens diretas de um ficheiro GTFS Schedule local."""
import csv
import io
import re
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from zipfile import BadZipFile, ZipFile

from jarvis.integrations.editor import normalize
from jarvis.integrations.project_files import safe_path
from jarvis.local_registers import saved_day

REQUEST = re.compile(
    r'(?:consulta (?:os )?)?horários de "([^"\r\n]{1,120})" para "([^"\r\n]{1,120})"'
    r' em (\d{4}-\d{2}-\d{2})(?: a partir das (\d{2}:\d{2}))? no gtfs "([^"\r\n]{1,500})"[.!]?',
    re.I,
)
FIELDS = {
    "agency.txt": ("agency_name", "agency_timezone"),
    "stops.txt": ("stop_id", "stop_name"),
    "routes.txt": ("route_id",),
    "trips.txt": ("route_id", "trip_id", "service_id"),
    "stop_times.txt": ("trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"),
    "calendar.txt": ("service_id", "start_date", "end_date"),
    "calendar_dates.txt": ("service_id", "date", "exception_type"),
    "frequencies.txt": ("trip_id",),
}
WEEK = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DAY = 86400
MAX_ENTRY = 128 * 1024 * 1024


@contextmanager
def rows(feed, name, optional=False):
    if name not in feed.namelist():
        if optional:
            yield ()
            return
        raise ValueError(f"Falta {name} na raiz do ficheiro GTFS.")
    info = feed.getinfo(name)
    if info.file_size > MAX_ENTRY or info.flag_bits & 1:
        raise ValueError(f"{name} excede o tamanho suportado ou está cifrado.")
    with feed.open(info) as compressed, io.TextIOWrapper(compressed, encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not set(FIELDS[name]).issubset(reader.fieldnames):
            raise ValueError(f"{name} não tem as colunas GTFS necessárias.")
        yield reader


def schedule_command(text, root):
    match = REQUEST.fullmatch(re.sub(r"^jarvis,\s*", "", text, flags=re.I))
    if not match:
        return None
    origin, destination, day, after, name = match.groups()
    day = date.fromisoformat(saved_day(day))
    if not 3 <= day.toordinal() <= date.max.toordinal() - 3:
        raise ValueError("Indica uma data suportada pelo horário.")
    after = time_value(after + ":00") if after else 0
    if after is None or after >= DAY:
        raise ValueError("Indica uma hora entre 00:00 e 23:59.")
    path = safe_path(root, name)
    if path.suffix.casefold() != ".zip" or not path.is_file() or path.stat().st_size > MAX_ENTRY:
        raise ValueError("Indica um ZIP GTFS do projeto com até 128 MB.")
    try:
        with ZipFile(path) as feed:
            return schedule(feed, path.relative_to(root).as_posix(), day, after, origin, destination)
    except (BadZipFile, UnicodeError, csv.Error) as error:
        raise ValueError("Não consegui ler o ZIP ou as tabelas do horário GTFS.") from error


def resolve_stop(feed, requested):
    token = normalize(requested).strip()
    if not token:
        raise ValueError("Indica o nome ou o identificador da paragem.")
    matches = defaultdict(set)
    with rows(feed, "stops.txt") as stops:
        for row in stops:
            identifier, label = row["stop_id"], row["stop_name"] or row["stop_id"]
            if not identifier:
                continue
            if requested.startswith("id:"):
                if identifier == requested[3:]:
                    return {identifier}, label
            elif token in normalize(label):
                matches[label].add(identifier)
    exact = [(label, ids) for label, ids in matches.items() if normalize(label) == token]
    if exact:
        return set().union(*(ids for _, ids in exact)), exact[0][0]
    if not matches:
        raise ValueError(f"Não encontrei a paragem {requested}.")
    if len(matches) == 1:
        label, ids = next(iter(matches.items()))
        return ids, label
    labels = [f'{label} · id:{min(matches[label])}' for label in sorted(matches)[:8]]
    raise ValueError(f"Encontrei várias paragens para {requested}. Indica o nome completo ou um dos IDs.\n" + "\n".join(labels))


def time_value(value):
    match = re.fullmatch(r"(\d{1,2}):([0-5]\d):([0-5]\d)", value or "")
    if not match:
        return None
    hours, minutes, seconds = map(int, match.groups())
    return 3600 * hours + 60 * minutes + seconds if hours < 72 else None


def time_text(seconds):
    days, seconds = divmod(seconds, DAY)
    hour, remainder = divmod(seconds, 3600)
    suffix = f" (+{days} dia)" if days else ""
    return f"{hour:02}:{remainder // 60:02}{suffix}"


def active_days(feed, requested):
    days = [requested - timedelta(days=offset) for offset in range(3)]
    by_date = {day.strftime("%Y%m%d"): (day, set()) for day in days}
    with rows(feed, "calendar.txt", optional=True) as regular:
        for row in regular:
            for stamp, (day, active) in by_date.items():
                if (row["start_date"] or "") <= stamp <= (row["end_date"] or "") and row.get(WEEK[day.weekday()]) == "1":
                    active.add(row["service_id"])
    with rows(feed, "calendar_dates.txt", optional=True) as exceptions:
        for row in exceptions:
            if row["date"] in by_date:
                active = by_date[row["date"]][1]
                if row["exception_type"] == "1":
                    active.add(row["service_id"])
                elif row["exception_type"] == "2":
                    active.discard(row["service_id"])
    return {day: active for day, active in by_date.values()}


def schedule(feed, source, day, after, origin, destination):
    starts, start_label = resolve_stop(feed, origin)
    ends, end_label = resolve_stop(feed, destination)
    if starts & ends:
        raise ValueError("Escolhe paragens diferentes para a origem e o destino.")
    by_date = active_days(feed, day)
    offsets = defaultdict(list)
    for service_day, active in by_date.items():
        for service in active:
            offsets[service].append((day - service_day).days * DAY)
    with rows(feed, "frequencies.txt", optional=True) as frequency:
        frequencies = {row["trip_id"] for row in frequency}
    with rows(feed, "trips.txt") as trip_rows:
        trips = {row["trip_id"]: row for row in trip_rows
                 if row["service_id"] in offsets and row["trip_id"] not in frequencies}
    visits = defaultdict(list)
    with rows(feed, "stop_times.txt") as times:
        for row in times:
            if row["trip_id"] not in trips:
                continue
            stop, order = row["stop_id"], row["stop_sequence"] or ""
            if not order.isdigit() or len(order) > 9:
                continue
            if stop in starts and row.get("pickup_type") not in {"1", "2", "3"}:
                value = time_value(row["departure_time"])
                if value is not None:
                    visits[row["trip_id"]].append((int(order), True, value))
            elif stop in ends and row.get("drop_off_type") not in {"1", "2", "3"}:
                value = time_value(row["arrival_time"])
                if value is not None:
                    visits[row["trip_id"]].append((int(order), False, value))
    with rows(feed, "routes.txt") as routes:
        route_names = {row["route_id"]: row.get("route_short_name") or row.get("route_long_name") or row["route_id"] for row in routes}
    found = []
    for trip_id, stops in visits.items():
        trip = trips[trip_id]
        label = route_names.get(trip["route_id"], trip["route_id"])
        departure = None
        for _, start, stamp in sorted(stops, key=lambda stop: stop[0]):
            if start:
                departure = stamp
            elif departure is not None and stamp >= departure:
                for offset in offsets[trip["service_id"]]:
                    if after <= departure - offset < DAY:
                        found.append((departure - offset, stamp - offset, label))
                departure = None
    with rows(feed, "agency.txt") as agencies:
        details = list(agencies)
    zones = sorted({row["agency_timezone"] for row in details if row["agency_timezone"]})
    lines = [f"{start_label} → {end_label} · {day:%d/%m/%Y}", f"Horário programado · {', '.join(zones)} · {source}"]
    for start, end, label in sorted(set(found))[:15]:
        lines.append(f"- {time_text(start)} → {time_text(end)} · {label}")
    if not found:
        lines.append("Não encontrei viagens diretas com hora definida para essas paragens e data no ficheiro.")
    if frequencies:
        lines.append("O ficheiro também contém serviços por frequência. A consulta apresenta viagens com horário fixo.")
    return "\n".join(lines)
