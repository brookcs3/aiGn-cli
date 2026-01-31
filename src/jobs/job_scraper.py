import os
import subprocess
import pandas as pd
from jobspy import scrape_jobs
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

subprocess.run(["gum"], stdout=subprocess.PIPE, text=True)

def get_input(prompt, default_val):
    val = input(f"🔹 {prompt} [{default_val}]: ").strip()
    return val if val else default_val

def generate_markdown(df, filename="latest_results.md", include_descriptions=False):
    md_content = f"# 🕵️ Job Search Results\n\n"
    md_content += f"**Found {len(df)} jobs.**\n\n"

    # Select specific columns if they exist
    cols = ['title', 'company', 'location', 'job_url', 'site']
    existing_cols = [c for c in cols if c in df.columns]

    for _, row in df[existing_cols + (['description'] if 'description' in df.columns else [])].iterrows():
        title = row.get('title', 'N/A')
        company = row.get('company', 'N/A')
        loc = row.get('location', 'N/A')
        url = row.get('job_url', '#')
        site = row.get('site', 'unknown')
        desc = row.get('description', '')

        md_content += f"## Company: {company}\n"
        md_content += f"Location: {loc}  \n"
        md_content += f"Source: {site}  \n"
        md_content += f"Apply Here {url}\n\n"
        md_content += f"## {title}\n\n"

        if include_descriptions and desc:
             md_content += "### 📝 Description\n"
             md_content += f"{desc}\n\n"

        md_content += "---\n\n"

    with open(filename, "w") as f:
        f.write(md_content)
    return filename


def main():
    while True:
        clear_screen()
        print("# 🦄 Job Hunter Interactive 🦄\n")
        
        term = get_input("Job Title", "software engineer")
        location = get_input("Location", "San Francisco, CA")
        limit = int(get_input("Results Limit", "5"))
        
        print("\n🚀 Spinning up the scraper... (this might take a few seconds)")
        
        try:
            jobs = scrape_jobs(
                site_name=["indeed", "linkedin", "glassdoor"], 
                search_term=term,
                location=location,
                results_wanted=limit,
                hours_old=72,
                country_nameof='USA',
                linkedin_fetch_description=True
            )
            
            if jobs is not None and not jobs.empty:
                print(f"✨ Success! Found {len(jobs)} jobs.")
                
                # Save jobs to CSV
                jobs.to_csv("jobs.csv", index=False)
                print("💾 Saved to jobs.csv")
                                
                # Generate markdown WITHOUT descriptions for initial view
                md_file = generate_markdown(jobs, include_descriptions=False)

                print("👀 Displaying results in terminal...")
                # Removed the "-p" flag so it displays inline, no 'q' needed
                subprocess.run(["glow", md_file])
            else:
                input("\n❌ No jobs found. Press Enter to try again...")
                continue
                
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            input("Press Enter to continue...")

        # This will now appear immediately after the results are shown
        if subprocess.run(["gum", "confirm", "Tailored Cover Leter?"]).returncode != 1:
            print("👋 Happy Hunting!")
            break
        

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
