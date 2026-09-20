import argparse
import asyncio
import pandas as pd
from scraper import run_scraper
import sys

def main():
    parser = argparse.ArgumentParser(description="Job Crawler Agent")
    parser.add_argument('--keyword', type=str, required=True, help="Job title or keyword to search for")
    parser.add_argument('--location', type=str, required=True, help="Location for the job search")
    parser.add_argument('--region', type=str, default="auto", help="Market region: India, Global / US, or auto")
    parser.add_argument('--experience', type=int, default=None, help="Experience in years (0 to 45)")
    parser.add_argument('--output', type=str, default="jobs.csv", help="Output CSV filename")
    
    args = parser.parse_args()
    
    exp_info = f", Experience: {args.experience} Yrs" if args.experience is not None else ""
    print(f"[*] Crawling jobs for '{args.keyword}' in '{args.location}' (Region: {args.region}{exp_info})...")
    
    # Run the async scraper
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    jobs = asyncio.run(run_scraper(args.keyword, args.location, region=args.region, experience=args.experience))
    
    if not jobs:
        print("[!] No jobs found. Websites might have blocked the request with a CAPTCHA.")
        return
        
    print(f"[*] Found {len(jobs)} jobs across platforms.")
    
    # Save to CSV using pandas
    df = pd.DataFrame(jobs)
    df.to_csv(args.output, index=False)
    print(f"[*] Saved results to {args.output}")

if __name__ == "__main__":
    main()
