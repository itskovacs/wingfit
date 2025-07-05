import json
from datetime import datetime


def mywhoop_normalize(data) -> dict:
    data = json.loads(data)

    normalized_data = {}
    collections = ["sleep_collection", "recovery_collection", "cycle_collection"]

    fields = {
        "sleep_collection": {"sleep_performance_percentage": "whoop_sleepscore"},
        "recovery_collection": {
            "recovery_score": "whoop_recovery",
            "resting_heart_rate": "hr_resting",
            "hrv_rmssd_milli": "hrv",
        },
        "cycle_collection": {
            "strain": "whoop_strain",
            "max_heart_rate": "hr_max",
            "average_heart_rate": "hr_avg",
        },
    }

    for c in collections:
        records = data[c]["records"]

        for record in records:
            date = record.get("created_at")[:10]

            score = record.get("score", {})
            for key in fields[c]:
                value = score.get(key)
                if isinstance(value, float):
                    value = round(value)
                normalized_data.setdefault(date, {})[fields[c][key]] = value

            if c == "sleep_collection" and not record.get("nap", False):
                # Sleep data is too specific, we need some parsing, skip naps
                normalized_data.setdefault(date, {})["sleep_start"] = record.get("start")
                normalized_data.setdefault(date, {})["sleep_end"] = record.get("end")

                summary = record.get("score", {}).get("stage_summary", {})
                in_bed = round(summary.get("total_in_bed_time_milli", 0) / 60000)
                awake = round(summary.get("total_awake_time_milli", 0) / 60000)
                normalized_data.setdefault(date, {})["sleep_asleep"] = in_bed - awake
                normalized_data.setdefault(date, {})["sleep_total"] = in_bed

    return normalized_data


def whoop_normalize(): ...


def applewatch_normalize(data) -> dict:
    data = json.loads(data)["data"]["metrics"]

    fields = {
        "step_count ": "steps",
        "apple_stand_time": "stand_time",
        "heart_rate": {
            "Min": "hr_min",
            "Max": "hr_max",
            "Avg": "hr_avg",
        },
        "resting_heart_rate": "hr_resting",
        "heart_rate_variability": "hrv",
        "sleep_analysis": "__",
    }
    to_iso = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z").isoformat()

    normalized_data = {}

    for metric in data:
        metric_name = metric.get("name")
        if metric_name not in fields:
            # We don't want to store this field for now
            continue

        wingfit_key = fields[metric_name]

        for d in metric.get("data"):
            # Retrieve only Apple Watch source data when source available
            if d.get("source") and ("Watch" not in d.get("source")):
                continue

            date = d.get("date")[:10]

            # Sleep data is too specific, we need some parsing
            if metric_name == "sleep_analysis":
                sleep_asleep = round(d.get("totalSleep", 0) * 60)
                if not sleep_asleep:
                    continue

                sleep_start = to_iso(d.get("sleepStart"))
                sleep_end = to_iso(d.get("sleepEnd"))
                sleep_total = sleep_asleep + round(d.get("awake") * 60)

                normalized_data.setdefault(date, {})["sleep_asleep"] = sleep_asleep
                normalized_data.setdefault(date, {})["sleep_start"] = sleep_start
                normalized_data.setdefault(date, {})["sleep_end"] = sleep_end
                normalized_data.setdefault(date, {})["sleep_total"] = sleep_total
                continue

            # Multiple fields to retrieve, is a dict
            if isinstance(wingfit_key, dict):
                for key in wingfit_key:
                    value = d[key]
                    if isinstance(value, float):
                        value = round(value)
                    normalized_data.setdefault(date, {})[wingfit_key[key]] = value

            # Single field to retrieve: qty
            else:
                value = d.get("qty")
                if isinstance(value, float):
                    value = round(value)
                normalized_data.setdefault(date, {})[wingfit_key] = value

    return normalized_data
