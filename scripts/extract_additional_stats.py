from bs4 import BeautifulSoup
import pandas as pd
import sys

# Usage
# python extract_additional_stats.py SAMPLE.html SAMPLE.csv

if len(sys.argv) != 3:
    print("Usage: python extract_additional_stats.py <input_html> <output_csv>")
    sys.exit(1)

html_path = sys.argv[1]
output_path = sys.argv[2]

# Read and parse HTML
with open(html_path, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Find the 'Additional Statistics' table
header = soup.find("h2", string="Additional Statistics")
if not header:
    print("Error: 'Additional Statistics' section not found.")
    sys.exit(1)

table = header.find_next("table")
if not table:
    print("Error: No table found after 'Additional Statistics' header.")
    sys.exit(1)

# Parse table 
rows = table.find_all("tr")
headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
data = []
for row in rows[1:]:
    cols = [td.get_text(strip=True) for td in row.find_all("td")]
    data.append(cols)

df = pd.DataFrame(data, columns=headers)

# Save to CSV
df.to_csv(output_path, index=False)
print(f"Saved 'Additional Statistics' table to {output_path}")