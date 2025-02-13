import os
import re
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

def extract_front_matter(soup):
    # Extract front matter metadata from HTML
    front_matter = {}
    title_tag = soup.find('h1', class_='post-title')
    if title_tag:
        front_matter['title'] = title_tag.get_text().strip()
    else:
        front_matter['title'] = "Untitled"

    date_tag = soup.find('time')
    if date_tag:
        date_str = date_tag.get('datetime') or date_tag.get_text()
        front_matter['date'] = date_str.strip()
    else:
        front_matter['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    return front_matter

def convert_utc_to_timezone(time_str, tz_str):
    # Parse the UTC time string into a datetime object, considering possible millisecond part
    # Use `[:-1]` to remove the final `Z` before parsing
    try:
        utc_time = datetime.strptime(time_str[:-1], "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        utc_time = datetime.strptime(time_str[:-1], "%Y-%m-%dT%H:%M:%S")

    utc_zone = pytz.timezone('UTC')
    utc_time = utc_zone.localize(utc_time)

    target_zone = pytz.timezone(tz_str)
    local_time = utc_time.astimezone(target_zone)

    return local_time.strftime("%Y-%m-%d %H:%M:%S")

def generate_front_matter(data):
    fm = "---\n"
    fm += f"title: {data['title']}\n"
    fm += f"updated: {data['updated']}\n"
    fm += f"date: {data['date']}\n"
    fm += f"categories: {data['categories']}\n"
    if data['tags']:
        fm += "tags:\n" + "\n".join(f"  - {tag}" for tag in data['tags'])
    return fm + "\n---\n\n"

def html_to_markdown(soup):
    # Locate the div containing the post body
    post_body = soup.find("div", class_="post-body")
    if not post_body:
        return ""

    markdown = ""

    for elem in post_body.children:
        if elem.name == 'p':
            # Handle paragraph content, converting links and inline code
            markdown += ''.join([handle_element(child) for child in elem.children])
            markdown += "\n\n"

        elif elem.name and elem.name.startswith('h'):
            # Handle headers
            header_text = elem.get_text(strip=True)
            header_level = int(elem.name[1])  # Extracts level from 'h1', 'h2', etc.
            markdown += f"{'#' * header_level} {header_text}\n\n"

        elif elem.name == 'figure' and elem.get('class') == ['highlight', 'plaintext']:
            # Handle code block within <figure> elements
            td_code = elem.find('td', class_='code')
            if td_code:
                code_lines = [span.get_text().rstrip() for span in td_code.find_all('span', class_='line')]
                markdown += f"\n```\n{'\n'.join(code_lines).strip()}\n```\n"

        elif elem.name == 'table':
            # Handle tables
            headers = [th.get_text(strip=True) for th in elem.find_all('th')]
            rows = elem.find_all('tr')[1:]
            markdown_table = []
            markdown_table.append(" | ".join(headers))
            markdown_table.append(" | ".join(["---"] * len(headers)))

            for row in rows:
                columns = [td.get_text(strip=True) for td in row.find_all('td')]
                markdown_table.append(" | ".join(columns))

            markdown += "\n".join(markdown_table) + "\n\n"

    return markdown.strip()

def handle_element(element):
    """Helper function to convert HTML elements to Markdown."""
    if element.name == 'a':
        # Convert <a> to Markdown link
        return f"[{element.text}]({element.get('href')})"
    elif element.name == 'code':
        # Convert <code> to inline code in Markdown
        return f"`{element.get_text()}`"
    elif str(element).startswith('<br'):
        # Convert <br> to newline
        return '\n\n'
    else:
        # Otherwise, return the element as text
        return str(element)

def process_html_file(html_path, output_dir):
    # Process a single HTML file
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        front_matter = {}

        front_matter['title'] = soup.find('h1', class_='post-title').get_text(strip=True)
        time_tag = soup.find('time', itemprop='dateCreated datePublished')
        published_time = time_tag.get_text(strip=True) if time_tag else None

        category_tag = soup.find('span', itemprop='name')
        front_matter['categories'] = category_tag.get_text(strip=True) if category_tag else None

        front_matter['updated'] = convert_utc_to_timezone(soup.find('meta', property='article:published_time')['content'], 'Asia/Shanghai')
        front_matter['date'] = convert_utc_to_timezone(soup.find('meta', property='article:modified_time')['content'], 'Asia/Shanghai')

        front_matter['tags'] = [tag['content'] for tag in soup.find_all('meta', property='article:tag')]

        fm = generate_front_matter(front_matter)
        markdown_content = html_to_markdown(soup)

        # Generate output file name based on parent directory name
        parent_dir_name = os.path.basename(os.path.dirname(html_path))
        output_path = os.path.join(output_dir, f"{parent_dir_name}.md")

        with open(output_path, 'w', encoding='utf-8') as md_file:
            md_file.write(fm + markdown_content)

        print(f"Conversion successful: {output_path}")

def batch_convert_html_to_markdown(input_dir, output_dir):
    # Batch convert HTML files to Markdown
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.html'):
                html_path = os.path.join(root, file)
                process_html_file(html_path, output_dir)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Hexo HTML to Markdown Converter')
    parser.add_argument('-i', '--input', required=True, help='Input directory (containing HTML files)')
    parser.add_argument('-o', '--output', required=True, help='Output directory (to save Markdown files)')
    args = parser.parse_args()

    batch_convert_html_to_markdown(args.input, args.output)