import datetime
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from starlette.responses import FileResponse

app = FastAPI()
# Send a GET request to the API
url = "https://www.investorgain.com/report/live-ipo-gmp/331/?r2"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
response = requests.get(url, headers=headers)


@app.get("/ipo")
async def root(sort: bool = False):
    # If the GET request is successful, the status code will be 200
    if response.status_code == 200:
        # Get the content of the response
        page_content = response.content

        # Create a BeautifulSoup object and specify the parser
        soup = BeautifulSoup(page_content, 'html.parser')

        # Find the table with the class "table table-bordered"
        table = soup.find('table')

        if table is None:
            return "Table not found"
        else:
            headers = table.find_all('thead')
            hdata = []
            for header in headers:
                hc = header.find_all('a')
                for h in hc:
                    hdata.append(h.text)

            # Find all the rows in the table
            rows = table.find_all('tr')

            # Create a list to store the data
            data = []

            # Iterate over each row
            for row in rows:
                # Find all the columns in the row
                cols = row.find_all('td')

                # Create a list to store the column data
                cols_data = []

                # Iterate over each column
                for col in cols:
                    # Get the text of the column
                    col_text = col.text.strip()

                    if not col_text:
                        if col.find('img'):
                            col_text = col.find('img').attrs['alt'].split(' ')[-1]
                    # Append the column data to the list
                    cols_data.append(col_text)

                # Append the row data to the list
                data.append(cols_data)

            # Create a pandas DataFrame from the data
            df = pd.DataFrame(data[1:], columns=data[1])
            df.columns = hdata
            df.dropna(subset=['Price'], inplace=True)

            # Convert 'Fire Rate' column to numeric (assuming it's a string representation of a fraction)
            df['Fire Rating'] = df['Fire Rating'].apply(lambda x: int(x.split('/')[0]))
            df['Open'] = df['Open'].apply(
                lambda x: datetime.datetime.strptime((x + "-" + datetime.datetime.today().year.__str__()),
                                                     '%d-%b-%Y').date() if x != '' else None)
            df['Close'] = df['Close'].apply(
                lambda x: datetime.datetime.strptime((x + "-" + datetime.datetime.today().year.__str__()),
                                                     '%d-%b-%Y').date() if x != '' else None)

            # Extract the numeric percentage from 'Est Listing' column and convert to float
            df['Est Listing Percentage'] = df['Est Listing'].apply(
                lambda x: float(re.search(r'\((\d+.\d+)%\)', x).group(1)) if pd.notna(x) and re.search(
                    r'\((\d+.\d+)%\)', x) else None)

            # Today's date (assuming you want to use the script execution date)
            today = pd.to_datetime('today').date()

            # Filter DataFrame
            filtered_df = df[(df['Fire Rating'] >= 3) & (df['Open'] <= today if df['Open'] is not None else True) & (
                df['Close'] >= today if df['Close'] is not None else True)]

            # Sort the DataFrame by 'Est Listing Percentage' in descending order
            if sort:
                filtered_df = filtered_df.sort_values(by='Est Listing Percentage', ascending=False)

            # Remove columns not required
            filtered_df = filtered_df[filtered_df.columns.drop('Est Listing Percentage')]
            filtered_df = filtered_df[filtered_df.columns.drop('GMP Updated')]
            filtered_df = filtered_df[filtered_df.columns.drop('Lot')]

            # Generate HTML table content
            html_content = filtered_df.to_html(index=False)

            # Save the HTML content (optional)
            with open('template.html', 'r') as f:
                template = f.read()
                with open("static/index.html", 'w') as out:
                    out.write(template)
                    out.write(html_content)
                    out.close()

            return FileResponse('static/index.html')
    else:
        print("Failed to retrieve the page")


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
