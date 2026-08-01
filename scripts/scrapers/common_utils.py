import re
from bs4 import BeautifulSoup

def remove_site_noise(soup):
    """
    Strips non-content noise elements like header, footer, navigation menus,
    sidebar links, cookie banners, and fast-link widgets from BeautifulSoup object.
    """
    noise_selectors = [
        'header', 'footer', 'nav', '#header', '#footer', '.sidebar',
        '.avia-cookie-consent', '.pranala-cepat', '.widget', '#socket',
        '.main_menu', '.sub_menu', '.av-main-nav-wrap', '.entry-footer',
        '.related_posts', '#comments', '.page-title'
    ]

    for sel in noise_selectors:
        for el in soup.select(sel):
            el.decompose()

    return soup

def clean_text(text):
    """
    Cleans raw text string by removing mid-sentence newlines, normalizing spaces,
    and stripping unwanted unicode noise.
    """
    if not text:
        return ""
    
    # Remove unwanted replacement characters
    text = text.replace('\ufffd', '').replace('', '')
    # Remove mid-sentence line breaks
    text = re.sub(r'(\w+)\n(\w+)', r'\1 \2', text)
    # Normalize multiple whitespace characters
    text = re.sub(r'[ \t]+', ' ', text)
    # Normalize multiple newlines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_table_with_icons(table):
    """
    Parses an HTML <table> element and explicitly converts Elementor/FontAwesome
    checkmark icons (<i class="fas fa-check"> / <i class="fas fa-minus"> / <span class="avia-font-icon">)
    into readable text 'Ya (✔)' or 'Tidak (—)'.
    """
    rows = []
    for tr in table.find_all('tr'):
        cols = []
        for td in tr.find_all(['td', 'th']):
            if td.name == 'th':
                cols.append(clean_text(td.get_text(" ", strip=True)))
                continue

            has_check = False
            has_minus = False

            icon_tags = td.find_all(['i', 'span', 'div'])
            for icon in icon_tags:
                classes = " ".join(icon.get('class', []))
                if 'fa-check' in classes or 'avia-font-icon' in classes or 'check' in classes:
                    has_check = True
                elif 'fa-minus' in classes or 'minus' in classes or 'dash' in classes or 'times' in classes:
                    has_minus = True

            text = clean_text(td.get_text(" ", strip=True))

            if has_check or '✔' in text:
                cols.append("Ya (✔)")
            elif has_minus or '—' in text:
                cols.append("Tidak (—)")
            elif text:
                cols.append(text)
            else:
                cols.append("Tidak (—)")

        if cols:
            rows.append(cols)
    return rows

def convert_links_to_markdown(soup):
    """
    Converts HTML <a> tags into Markdown links [Text](URL) preserving hyperlinks.
    """
    for a in soup.find_all('a', href=True):
        link_text = clean_text(a.get_text(" ", strip=True))
        link_url = a['href']
        if link_text and not link_url.startswith('#') and not link_url.startswith('javascript:'):
            if not link_url.startswith('http'):
                link_url = "https://pmb.uii.ac.id" + link_url
            a.replace_with(f" [{link_text}]({link_url}) ")
    return soup

def extract_aria_control_tabs(soup):
    """
    Extracts Elementor 3.x nested tabs (.e-n-tabs) by matching button aria-controls to panel IDs.
    Returns dict: { "Tab Name": panel_soup }
    """
    tabs_dict = {}
    buttons = soup.select('.e-n-tab-title')
    
    seen_controls = set()
    for btn in buttons:
        title = clean_text(btn.get_text(" ", strip=True))
        controls = btn.get('aria-controls', '')
        if title and controls and controls not in seen_controls:
            seen_controls.add(controls)
            panel = soup.find(id=controls)
            if panel:
                tabs_dict[title] = panel

    return tabs_dict

def extract_eael_tabs(soup):
    """
    Extracts Essential Addons for Elementor Tabs (.eael-advance-tabs).
    Returns dict: { "Tab Name": panel_soup }
    """
    tabs_dict = {}
    eael_tabs = soup.select('.eael-advance-tabs')
    for tab_container in eael_tabs:
        nav_items = tab_container.select('.eael-tab-nav-item')
        content_items = tab_container.select('.eael-tab-content-item')
        for i, nav in enumerate(nav_items):
            title = clean_text(nav.get_text(" ", strip=True))
            if title and i < len(content_items):
                tabs_dict[title] = content_items[i]
    return tabs_dict

def format_question_and_options(raw_text):
    """
    Parses concatenated exam question text into numbered questions and separate options A, B, C, D, E.
    """
    if not raw_text:
        return ""
    
    # 1. Put line break before options A., B., C., D., E.
    text = re.sub(r'(\s+|^)([A-E]\.\s+)', r'\n   - \2', raw_text)
    
    # 2. Put line break between end of option E and next question
    lines = text.split('\n')
    formatted_blocks = []
    q_count = 1

    for line in lines:
        l = line.strip()
        if not l:
            continue

        if l.startswith('- '):
            # Check if option E has a question concatenated after it
            # e.g. "- E. Memperingati meninggalnya Husein bin Ali Bacaan..."
            m = re.match(r'(- [A-E]\.\s+.*?)(?=\s+[A-Z0-9\u0600-\u06FF][^\?]+\?|$)', l)
            if m:
                opt_part = m.group(1).strip()
                rest_part = l[len(opt_part):].strip()
                formatted_blocks.append(opt_part)
                if rest_part:
                    formatted_blocks.append(f"\n**Soal {q_count}**: {rest_part}")
                    q_count += 1
            else:
                formatted_blocks.append(l)
        else:
            formatted_blocks.append(f"\n**Soal {q_count}**: {l}")
            q_count += 1

    return "\n".join(formatted_blocks).strip()
