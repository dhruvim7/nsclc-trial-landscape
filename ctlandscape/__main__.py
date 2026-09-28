"""Command line entry point.

    python -m ctlandscape check              live test against the API (3 records)
    python -m ctlandscape run                full pipeline, using cached data if present
    python -m ctlandscape run --refresh      re-download first
"""

import argparse
import json
import sys

import requests

from . import fetch, figures, parse, report, settings


def run(refresh):
    studies = fetch.fetch_all(refresh=refresh)
    df = parse.to_dataframe(studies)
    print(f"{len(df):,} interventional trials after de-duplication and filtering.")

    quality = parse.quality_report(df)
    print("Missing values (%):", quality)
    broken = [c for c in ("status", "sponsor_class", "start_date") if quality[c] == 100.0]
    if broken or (df["phase"].astype(str) == "No phase").all():
        sys.exit(f"Stopping: fields {broken or ['phase']} are empty for every trial. "
                 "The API response shape has probably changed; run `python -m ctlandscape check`.")

    df.to_csv(settings.CLEAN_FILE, index=False)
    meta = json.loads(settings.META_FILE.read_text()) if settings.META_FILE.exists() else {}
    note = (f"Source: ClinicalTrials.gov, interventional trials matching '{settings.CONDITION}', "
            f"downloaded {meta.get('downloaded_on', 'n/a')}.")
    paths = figures.all_figures(df, note)
    print(f"Wrote {len(paths)} figures to {settings.FIG_DIR.name}/")
    print(f"Wrote {report.write(df, quality).relative_to(settings.ROOT)}")
    from .analyze import sanity_checks
    for warning in sanity_checks(df):
        print("CHECK:", warning)


def main():
    parser = argparse.ArgumentParser(prog="ctlandscape")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    run_p = sub.add_parser("run")
    run_p.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "check":
            fetch.check()
        else:
            run(args.refresh)
    except requests.HTTPError as err:
        code = err.response.status_code if err.response is not None else "?"
        hint = (" A 403 usually means the request was blocked before reaching the API "
                "(office network, VPN or firewall). Try another network." if code == 403 else "")
        sys.exit(f"ClinicalTrials.gov returned HTTP {code}.{hint}")
    except requests.ConnectionError:
        sys.exit("Could not reach clinicaltrials.gov. Check your internet connection.")


if __name__ == "__main__":
    main()
