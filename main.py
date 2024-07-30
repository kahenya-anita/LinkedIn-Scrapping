import os
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from rich.progress import track
from rich.console import Console
from rich.table import Table
from langchain_openai import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence  

from dotenv import load_dotenv

load_dotenv()

# Global variables
df = pd.DataFrame(columns=['Title', 'Location', 'Company', 'Link', 'Description'])
console = Console()
table = Table(show_header=True, header_style="bold")

# Get user input
console.print("Enter Job Title :", style="bold green", end=" ")
inputJobTitle = input()
console.print("Enter Job Location :", style="bold green", end=" ")
inputJobLocation = input()
console.print("Enter Your Skills (comma separated):", style="bold green", end=" ")
inputSkills = input().split(',')

async def scrapeJobDescription(url):
    driver = await DriverOptions()
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    try:
        jobDescription = soup.find("div", class_="show-more-less-html__markup").text.strip()
        driver.quit()
        return jobDescription
    except:
        driver.quit()
        return ""

async def DriverOptions():
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    return driver

async def scrapeLinkedin():
    global df
    global inputJobTitle
    global inputJobLocation

    driver = await DriverOptions()
    counter = 0
    pageCounter = 1

    while True:
        try:
            driver.get(f"https://www.linkedin.com/jobs/search/?&keywords={inputJobTitle}&location={inputJobLocation}&refresh=true&start={counter}")

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            ulElement = soup.find('ul', class_='jobs-search__results-list')
            liElements = ulElement.find_all('li')

            for item in track(liElements, description=f"Linkedin - Page: {pageCounter}"):
                jobTitle = item.find('h3', class_='base-search-card__title').text.strip()
                jobLocation = item.find('span', class_='job-search-card__location').text.strip()
                jobCompany = item.find("h4", class_="base-search-card__subtitle").text.strip()
                jobLink = item.find_all("a")[0]['href']

                jobDescription = await scrapeJobDescription(jobLink)

                if jobTitle and jobLocation and jobCompany and jobLink:
                    df = pd.concat([df, pd.DataFrame({'Title': [jobTitle], 'Location': [jobLocation], 'Company': [jobCompany], 'Link': [f'[link={jobLink}]Click here[/link]'], 'Description': [jobDescription]})])

            console.print("Scrape Next Page? (y/n) :", style="bold yellow", end=" ")
            continueInput = input()

            if continueInput == "n":
                break

            counter += 25
            pageCounter += 1

        except:
            break

    driver.quit()

def extract_job_requirements(description):
    prompt = """
    Extract the job requirements from the following job description:
    {job_description}
    
    Requirements:
    """
    prompt_template = PromptTemplate(template=prompt, input_variables=["job_description"])
    sequence = RunnableSequence(template=prompt_template)

    return sequence.run(job_description=description)

def filter_jobs_by_skills(description, skills):
    requirements = extract_job_requirements(description)
    required_skills = [skill.strip().lower() for skill in requirements.split(',')]
    matched_skills = [skill for skill in skills if skill.strip().lower() in required_skills]
    
    return len(matched_skills) / len(required_skills) >= 0.5  # 50% match threshold

async def main():
    await scrapeLinkedin()

    # Create table
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Link")
    table.add_column("Description")

    # Iterate over dataframe and filter jobs
    for index, row in df.iterrows():
        if filter_jobs_by_skills(row['Description'], inputSkills):
            table.add_row(
                f"{row['Title']}",
                f"{row['Company']}",
                f"{row['Location']}",
                f"{row['Link']}",
                f"{(row['Description'])[:20]}..."
            )

    console.print(table)

if __name__ == '__main__':
    asyncio.run(main())
