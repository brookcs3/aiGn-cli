import argparse
import csv
from jobspy import scrape_jobs

def main():
    parser = argparse.ArgumentParser(description="Scrape jobs from multiple job boards.")
    parser.add_argument("-t", "--term", type=str, default="software engineer", help="Job search term")
    parser.add_argument("-l", "--location", type=str, default="San Francisco, CA", help="Job location")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Number of results to fetch")
    parser.add_argument("-o", "--output", type=str, default="jobs.csv", help="Output CSV filename")

    args = parser.parse_args()

    print(f"🚀 Scraping for '{args.term}' in '{args.location}' (Target: {args.limit} jobs)...")

    jobs = scrape_jobs(
        site_name=["indeed", "linkedin", "zip_recruiter", "glassdoor"],
        search_term=args.term,
        location=args.location,
        results_wanted=args.limit,
        hours_old=72,
        country_nameof='USA',
    )
    
    print(f"✨ Found {len(jobs)} jobs")
    if not jobs.empty:
        # print(jobs[['title', 'company', 'company_url']].head())
        jobs.to_csv(args.output, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
        print(f"💾 Saved per request to {args.output}")
    else:
        print("😕 No jobs found. Try broadening your search.")

if __name__ == "__main__":
    main()
