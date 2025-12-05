import io
import os
import re
import subprocess 
from html.parser import HTMLParser
import zipfile 

# ==============================================
# DSL Dictionary Converter - Enhanced Complete Version
# Version SOBAE - Full DSL Tags Support
# ==============================================

print("="*60)
print("DSL Dictionary Converter - Enhanced Complete Version")
print("By SOBAE - Fixed Color Tags")
print("="*60)

# --- 1. Check Dependencies ---

def check_command(command):
    """Check if a command is available on the system."""
    try:
        subprocess.check_output([command, '--version'], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    else:
        return True

if not check_command('python3'):
    print("ERROR: python3 is required!")
    exit(1)

# --- 2. User Prompt ---

print("="*60)
print("STEP 1: File Setup")
print("="*60)

skip_pyglossary = input("Do you already have the input file (TXT or MTXT) and want to proceed directly to DSL conversion? (y/n): ").strip().lower()

proceed_to_dsl = False

if skip_pyglossary == 'y':
    print("Skipping Pyglossary and proceeding directly to DSL conversion.")
    proceed_to_dsl = True
else:
    print("\n" + "="*60)
    print("  STEP 1: Run Pyglossary for manual conversion to MTXT")
    print("  (Please convert your source dictionary file manually now)")
    print("="*60)
    
    try:
        subprocess.call('pyglossary --cmd', shell=True)
    except Exception as e:
        print(f"Error running pyglossary: {e}")
        exit(1)

    print("\n" + "="*60)
    answer = input("STEP 2: Do you want to convert the resulting file to .dsl format? (y/n): ").strip().lower()

    if answer == "y":
        proceed_to_dsl = True

if not proceed_to_dsl:
    print("DSL conversion skipped. Exiting.")
    exit(0)

# ========== Get Input File and Metadata ==========

input_file = input("Enter input file path (e.g., MyDict.txt or MyDict.mtxt): ").strip()
while not os.path.isfile(input_file):
    print("File not found, try again.")
    input_file = input("Enter input file path: ").strip()

dict_name = os.path.splitext(os.path.basename(input_file))[0]
source_lang = ""
target_lang = ""
raw_content_lines = []

mtxt_header_count = 0
mtxt_separator_found = False
tab_separator_found = False

try:
    with io.open(input_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            raw_content_lines.append(line)
            
            if i < 200:
                stripped_line = line.strip()
                
                if stripped_line.startswith("##"):
                    mtxt_header_count += 1
                
                if "</>" in stripped_line:
                    mtxt_separator_found = True
                
                if "\t" in line and not line.startswith("##"):
                    tab_separator_found = True
                    
except Exception as e:
    print(f"❌ Error reading input file: {e}")
    exit(1)

file_extension = input_file.lower()

if file_extension.endswith('.mtxt'):
    is_mtxt = True
    print("File extension is .mtxt - Processing as MTXT format")
elif file_extension.endswith('.txt'):
    if mtxt_separator_found:
        is_mtxt = True
        print("File extension is .txt but content appears to be MTXT format (</> found)")
    else:
        is_mtxt = False
        print("File extension is .txt - Processing as Tab-separated TXT format")
else:
    if mtxt_separator_found:
        is_mtxt = True
        print("Detected MTXT format based on content (</> found)")
    elif tab_separator_found:
        is_mtxt = False
        print("Detected Tab-separated TXT format based on content")
    else:
        print("⚠️ Could not auto-detect file format")
        user_choice = input("Is this file MTXT format? (y/n): ").strip().lower()
        is_mtxt = (user_choice == 'y')
         
entries_list = []

def normalize_lang(user_input, default):
    if not user_input:
        return default
    
    u = user_input.strip().lower()

    if u in ("en", "eng", "english"):
        return "ENGLISH"
    if u in ("ar", "arabic", "ara"):
        return "ARABIC"
    if u in ("de", "ge", "ger", "german", "deutsch"):
        return "GERMAN"
    if u in ("fr", "fre", "french", "français"):
        return "FRENCH"
    if u in ("es", "spa", "spanish", "español"):
        return "SPANISH"
    if u in ("ru", "rus", "russian"):
        return "RUSSIAN"
    if u in ("zh", "chi", "chinese"):
        return "CHINESE"
    if u in ("ja", "jpn", "japanese"):
        return "JAPANESE"

    return user_input.strip().upper()
    
if is_mtxt:
    print("Processing as MTXT format...")
    
    content_lines = []
    for line in raw_content_lines:
        stripped = line.strip()
        
        if stripped.startswith("##name"):
            dict_name = stripped.split("\t", 1)[1].strip()
        elif stripped.startswith("##sourceLang"):
            source_lang = stripped.split("\t", 1)[1].strip()
        elif stripped.startswith("##targetLang"):
            target_lang = stripped.split("\t", 1)[1].strip()
        elif stripped.startswith("##"):
            continue
        else:
            clean_line = line.replace("\\n", "")
            content_lines.append(clean_line.rstrip("\n"))
            
    raw = "\n".join(content_lines)
    blocks = [b.strip() for b in raw.split("</>") if b.strip()]

    headword_entries = {}
    links_to_process = {}
    
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
            
        headword = lines[0]
        
        if len(lines) >= 2 and lines[1].startswith("@@@LINK="):
            target = lines[1].replace("@@@LINK=", "").strip()
            links_to_process[headword] = target
            continue
        
        if headword in headword_entries:
            existing_content = headword_entries[headword]
            new_content = "\n".join(lines[1:])
            
            if existing_content and new_content:
                headword_entries[headword] = existing_content + "\n[m1]\\ [/m]\n" + new_content
            elif new_content:
                headword_entries[headword] = existing_content + new_content
        else:
            headword_entries[headword] = "\n".join(lines[1:])

    word_groups = {}
    
    for headword in headword_entries:
        word_groups[headword] = [headword]
        
    for linked_word, main_word in links_to_process.items():
        if main_word in word_groups:
            word_groups[main_word].append(linked_word)
        else:
            word_groups[main_word] = [main_word, linked_word]
            headword_entries[main_word] = ""

    for main_head, all_headwords in word_groups.items():
        html_content = headword_entries.get(main_head, "")
        if html_content or all_headwords:
            entries_list.append({
                'headwords': all_headwords,
                'html': html_content
            })
            
    if not source_lang:
        source_lang = normalize_lang(input("Enter Source Language (en/ar/de/fr/es/ru/zh/ja): "), "ENGLISH")

    if not target_lang:
        target_lang = normalize_lang(input("Enter Target Language (en/ar/de/fr/es/ru/zh/ja): "), "ARABIC")
            
else:
    print("Processing as Tab-separated TXT format...")
    
    headword_entries = {}
    
    for line in raw_content_lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("##"):
            continue
            
        parts = line.split("\t", 1)
        
        if len(parts) != 2:
            continue
            
        head = parts[0].strip()
        html = parts[1].strip()
        
        headwords = [h.strip() for h in head.split("|") if h.strip()]
        
        if headwords and html:
            main_headword = headwords[0]
            
            if main_headword in headword_entries:
                existing_content = headword_entries[main_headword]['html']
                existing_headwords = headword_entries[main_headword]['headwords']
                
                for hw in headwords:
                    if hw not in existing_headwords:
                        existing_headwords.append(hw)
                
                headword_entries[main_headword]['html'] = existing_content + "\n[m1]\\ [/m]\n" + html
            else:
                headword_entries[main_headword] = {
                    'headwords': headwords,
                    'html': html
                }

    for entry_data in headword_entries.values():
        entries_list.append(entry_data)

    if not source_lang:
        source_lang = normalize_lang(input("Enter Source Language (en/ar/de/fr/es/ru/zh/ja): "), "ENGLISH")

    if not target_lang:
        target_lang = normalize_lang(input("Enter Target Language (en/ar/de/fr/es/ru/zh/ja): "), "ARABIC")


print(f"✅ Successfully loaded {len(entries_list)} entries.")

output_file = dict_name + ".dsl"
print(f"Output DSL file will be: {output_file}")

# ========== Enhanced HTML Parser with Full DSL Support ==========

# 🧠 THE SMART PARSER (قلب الكود المعدل)
# ========================================================

class AdvancedDSLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = ""
        self.stack = []  
        self.p_stack = [] 
        self.last_tag_was_br = False

    def emit(self, text):
        self.output += text
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        tag_lower = tag.lower()
        
        # 1. منطق الـ Paragraph الذكي
        if tag_lower == "p":
            style = attrs_dict.get('style', '').lower()
            
            # فحص المسافة البادئة
            if '2em' in style or 'padding-left:2em' in style.replace(" ", ""):
                margin_tag = "[m2]"
            else:
                margin_tag = "[m1]"
            
            # سطر جديد قبل الفقرة إذا لم يكن موجوداً
            if self.output and not self.output.endswith('\n'):
                self.emit("\n")
            
            self.emit(f"\t\t{margin_tag}")
            self.p_stack.append(margin_tag)
            return 

        # 2. منطق class="p" (يتحول للون الأخضر/التنسيق)
        if attrs_dict.get('class') == 'p':
            self.emit("[p]")
            self.stack.append(('special_p', attrs_dict)) 
            return 
        
        # 🟢 3. منطق القوائم المرقمة (ol و li)
        elif tag_lower == "ol":
            self.list_counter = 0 
            return

        elif tag_lower == "li":
            self.list_counter += 1 
            if self.output and not self.output.endswith('\n'):
                self.emit("\n")
            
            self.emit(f"\t\t[m2]") 
            self.emit(f"{self.list_counter}. ")
            
            self.stack.append((tag_lower, attrs_dict))
            return 
        
        # بقية التاقات (يتم إضافتها إلى الستاك قبل المعالجة لضمان الإغلاق)
        self.stack.append((tag_lower, attrs_dict))
        
        if tag_lower == "br":
            # نحول الـ br لسطر جديد ومسافة بادئة
            self.emit("\n\t")
        
        elif tag_lower == "font":
            color = attrs_dict.get("color", "")
            if color:
                clean = color.lstrip("#")
                self.emit(f"[c {clean}]")
            else:
                self.emit("[c]")
        
        elif tag_lower in ["b", "strong"]:
            self.emit("[b]")
        
        # 🟢 4. منطق عنوان قسم الكلام (i/em بدون class)
        elif tag_lower in ["i", "em"]:
            # نتحقق إذا كان الوسم يحتوي على أي class (مثل class="p"). إذا لم يكن، نعامله كـ POS.
            if not attrs_dict.get('class'):
                
                # 1. إخراج السطر الفارغ المطلوب: [m1]\ [/m]
                if self.output and not self.output.endswith('\n'):
                    self.emit("\n") 
                self.emit(f"\t\t[m1]\ [/m]\n")
                
                # 2. بدء سطر عنوان القسم: [m1][b]
                self.emit(f"\t\t[m1][b]") 
                
                # 3. فتح وسم <i>
                self.emit("[i]")
                
                # نستخدم اسم خاص لكي نعرف أن هذا وسم يجب أن يغلق [m1] و [b]
                self.stack[-1] = ('special_pos_i', attrs_dict) 
                return # تم التعامل معه بالكامل
            
            # إذا كان i/em يحتوي على class، نعامله كتنسيق عادي:
            self.emit("[i]") 
            
        elif tag_lower == "u":
            self.emit("[u]")
        elif tag_lower == "a":
            href = attrs_dict.get("href", "")
            if href.startswith("entry://") or href: 
                self.emit("[ref]")
                return # لا داعي لإضافته للستاك مرة أخرى هنا، لأنه أضيف أعلاه

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        
        # إغلاق الفقرة الهيكلية
        if tag_lower == "p":
            if self.p_stack:
                self.p_stack.pop()
                self.emit("[/m]")
            return
        
        # إغلاق ol
        if tag_lower == "ol":
            return

        if not self.stack: return

        # إغلاق class="p"
        if self.stack[-1][0] == 'special_p':
             self.emit("[/p]")
             self.stack.pop()
             return

        # إغلاق التاقات العادية
        for i in range(len(self.stack)-1, -1, -1):
            stack_tag, attrs_dict = self.stack[i]
            
            # 🟢 NEW: إغلاق وسم عنوان القسم
            if stack_tag == 'special_pos_i':
                self.emit("[/i][/b][/m]") # نغلق </i> و </b> و [m1]
                del self.stack[i]
                return
            
            if stack_tag == tag_lower:
                if tag_lower == "li": 
                    self.emit("[/m]")
                elif tag_lower == "font": self.emit("[/c]")
                elif tag_lower in ["b", "strong"]: self.emit("[/b]")
                elif tag_lower in ["i", "em"]: self.emit("[/i]") # هذا للـ <i> العادي
                elif tag_lower == "u": self.emit("[/u]")
                elif tag_lower == "a": 
                    self.emit("[/ref]") 
                del self.stack[i]
                return

    def handle_data(self, data):
        # 🟢 هنا السحر: تحويل المسافة غير المنكسرة لسطر فارغ DSL
        if data == '\xa0' or data.strip() == '&nbsp;':
            self.emit(r"\ ") # هذا سينتج شرطة مائلة ومسافة
            return
            
        if data.strip():
            clean_data = re.sub(r'\s+', ' ', data)
            # إضافة مسافة قبل الكلمة إذا لم تكن ملتصقة
            if self.output and self.output[-1] not in [' ', '\t', '\n', '[', ']'] and clean_data[0] not in ['.', ',', ';', ':']:
                 self.emit(' ' + clean_data)
            else:
                 self.emit(clean_data)

    def handle_entityref(self, name):
        # 🟢 التقاط الـ nbsp المكتوبة كـ entity
        if name == "nbsp":
            self.emit(r"\ ") 
        else:
            self.emit(f'&{name};')

    def close(self):
        super().close()
        result = self.output
        # تنظيف نهائي
        result = re.sub(r'(\[m\d\]\\ \[/m\]\s*)+', r'[m1]\\ [/m]\n', result)
        # إغلاق أي تاقات بقيت مفتوحة
        while self.p_stack:
            result += "[/m]"
            self.p_stack.pop()
        
        # إغلاق تاقات التنسيق المفتوحة
        for tag, _ in reversed(self.stack):
             # 🟢 يجب أن نغلق special_pos_i هنا أيضاً إذا لم يتم إغلاقه
             if tag == 'special_pos_i': result += "[/i][/b][/m]"
             elif tag == "font": result += "[/c]"
             elif tag in ["b", "strong"]: result += "[/b]"
             elif tag in ["i", "em"]: result += "[/i]"
             elif tag == 'special_p': result += "[/p]"

        return result.strip()



# ========== Helper Functions ==========

def convert_br_tags(html_content):
    """
    Convert HTML br tags to DSL format:
    - <br><br> or multiple <br> tags -> [m1]\ [/m] (empty line in DSL)
    - Single <br> -> \n\t (new line)
    """
    html_content = re.sub(
        r'(<br\s*/?>\s*){2,}', 
        '\n\t[m1]\\ [/m]\n\t', 
        html_content, 
        flags=re.IGNORECASE
    )
    
    html_content = re.sub(
        r'<br\s*/?>', 
        '\n\t', 
        html_content, 
        flags=re.IGNORECASE
    )
    
    return html_content

def convert_html_to_dsl(html_content):
    # تنظيف مسبق
    html_content = html_content.replace("&nbsp;", " ") # توحيد المسافات
    parser = AdvancedDSLParser()
    parser.feed(html_content)
    return parser.close()

def fix_phonetic_brackets(text):
    """Fix phonetic brackets while preserving DSL tags"""
    def repl(m):
        inner = m.group(1).strip()
        
        dsl_tags = ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9",
                   "b", "i", "u", "c", "s", "trn", "ex", "com", "ref", "url",
                   "sub", "sup", "lang", "p", "!trs", "*", "'",
                   "/m", "/b", "/i", "/u", "/c", "/s", "/trn", "/ex", "/com",
                   "/ref", "/url", "/sub", "/sup", "/lang", "/p", "/!trs", "/*", "/'",
                   "li", "/li", "ol", "/ol", "ul", "/ul"]
        
        for tag in dsl_tags:
            if inner == tag or inner.startswith(tag + " "):
                return f"[{inner}]"
        
        return "{" + inner + "}"

    return re.sub(r"\[([^\]]+)\]", repl, text)

def format_paragraphs_for_dsl(text):
    """Format text to match DSL Lingvo paragraph system"""
    lines = text.split('\n')
    formatted_lines = []
    in_margin_block = False
    current_margin = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('@'):
            if in_margin_block:
                formatted_lines.append("\t" + " " * (current_margin - 1) + "[/m]")
                in_margin_block = False
            
            formatted_lines.append("\t@ " + line[1:].strip())
            current_margin = 1
        
        elif re.match(r'^\[m[1-9]\]', line):
            margin_match = re.match(r'^\[m([1-9])\]', line)
            if margin_match:
                current_margin = int(margin_match.group(1))
                in_margin_block = True
                formatted_lines.append("\t" + " " * (current_margin - 1) + line)
            else:
                formatted_lines.append("\t" + line)
        
        elif line == '[/m]':
            if in_margin_block:
                formatted_lines.append("\t" + " " * (current_margin - 1) + line)
                in_margin_block = False
                current_margin = 1
        
        else:
            if in_margin_block:
                indent = "\t" + " " * (current_margin - 1)
                formatted_lines.append(indent + line)
            else:
                formatted_lines.append("\t" + line)
    
    if in_margin_block:
        formatted_lines.append("\t" + " " * (current_margin - 1) + "[/m]")
    
    return '\n'.join(formatted_lines)

def detect_wiktionary_structure(html_block):
    """Detect and convert typical Wiktionary structure"""
    result = html_block
    result = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n@ \1\n', result, flags=re.IGNORECASE)
    result = re.sub(r'<li[^>]*>(\d+\.)\s*(.*?)</li>', r'\n\t[m1]\1 \2[/m]', result, flags=re.IGNORECASE)
    result = re.sub(r'<i>(.*?)</i>', r'[i]\1[/i]', result, flags=re.IGNORECASE)
    result = re.sub(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', convert_wiktionary_link, result, flags=re.IGNORECASE)
    return result

def convert_wiktionary_link(match):
    href = match.group(1)
    text = match.group(2)
    if 'wiki' in href.lower() or 'wiktionary' in href.lower():
        return f'[url]{href}[/url]'
    return f'[ref]{text}[/ref]'

def validate_dsl_tags(text):
    """
    Validate DSL tags and fix common issues.
    UPDATED: Correctly handles tags with attributes like [c red] or [lang name="en"]
    """
    
    # 1. Simple Paired Tags (no attributes usually)
    simple_tags = [
        ('[b]', '[/b]'),
        ('[i]', '[/i]'),
        ('[u]', '[/u]'),
        ('[s]', '[/s]'),
        ('[trn]', '[/trn]'),
        ('[ex]', '[/ex]'),
        ('[com]', '[/com]'),
        ('[ref]', '[/ref]'),
        ('[url]', '[/url]'),
        ('[sub]', '[/sub]'),
        ('[sup]', '[/sup]'),
        ('[p]', '[/p]'),
        ('[!trs]', '[/!trs]'),
        ("[']", "[/']"),
        ('[*]', '[/*]'),
    ]
    
    result = text
    
    for open_tag, close_tag in simple_tags:
        open_count = result.count(open_tag)
        close_count = result.count(close_tag)
        
        if open_count > close_count:
            result += close_tag * (open_count - close_count)
        elif close_count > open_count:
            result = result.replace(close_tag, '', close_count - open_count)

    # 2. Complex Tags (with attributes) - handled via Regex
    # Matches [tag] or [tag ...] 
    complex_tags = [
        ('c', '[/c]'),
        ('lang', '[/lang]')
    ]

    for tag_name, close_tag in complex_tags:
        # Regex to match [tag] or [tag space...]
        # \[tag matches literal [tag
        # (?:\]|\s) matches either closing bracket ] OR a space
        pattern = r'\[' + tag_name + r'(?:\]|\s)'
        
        open_count = len(re.findall(pattern, result))
        close_count = result.count(close_tag)
        
        if open_count > close_count:
            result += close_tag * (open_count - close_count)
        elif close_count > open_count:
            # Safely remove extra closing tags
            result = result.replace(close_tag, '', close_count - open_count)
    
    # Check margin tags
    margin_pattern = r'\[m([1-9])\]'
    margin_tags = re.findall(margin_pattern, result)
    close_margin_count = result.count('[/m]')
    
    if len(margin_tags) > close_margin_count:
        result += '[/m]' * (len(margin_tags) - close_margin_count)
    
    return result

def clean_dsl_output(text):
    """Clean final DSL output"""
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = re.sub(r'[ \t]{2,}', ' ', line)
        line = line.rstrip()
        
        if line or line == '':
            cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
    return result

# ========== Write DSL File ==========

try:
    with io.open(output_file, "w", encoding="utf-16") as out:
        out.write(f'#NAME "{dict_name}"\n')
        out.write(f'#INDEX_LANGUAGE "{source_lang}"\n')
        out.write(f'#CONTENTS_LANGUAGE "{target_lang}"\n\n')

        total_entries = len(entries_list)
        for idx, entry in enumerate(entries_list, 1):
            headwords = entry['headwords']
            html_block = entry['html']
            
            

            for w in headwords:
                out.write(w + "\n")

            if not html_block:
                out.write("\t[m1][/m]\n")
                continue

            dsl_content = convert_html_to_dsl(html_block)
            
            if 'wiki' in html_block.lower() or 'wiktionary' in html_block.lower():
                dsl_content = detect_wiktionary_structure(dsl_content)
            
            dsl_content = fix_phonetic_brackets(dsl_content)
            dsl_content = format_paragraphs_for_dsl(dsl_content)
            dsl_content = validate_dsl_tags(dsl_content)
            dsl_content = clean_dsl_output(dsl_content)
            
            out.write(dsl_content + "\n")

    print(f"\n✅ DSL conversion completed successfully! File: {output_file}")
    
    dsl_conversion_success = True

except Exception as e:
    print(f"❌ Error during DSL conversion: {e}")
    import traceback
    traceback.print_exc()
    dsl_conversion_success = False

# --- 4. Compress Resources ---

if dsl_conversion_success:
    print("\n" + "="*60)
    print("STEP 3: Checking for resources folder and compressing it...")
    print("="*60)
    
    res_folder_path = input_file + "_res"

    print(f"Searching for resources folder: {res_folder_path}")

    if os.path.isdir(res_folder_path):
        zip_output_file = output_file + ".files.zip"

        print(f"Resources folder found. Starting ZIP compression to: {zip_output_file}")

        try:
            with zipfile.ZipFile(zip_output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(res_folder_path):
                    base_path_len = len(res_folder_path) + 1 
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = file_path[base_path_len:] 

                        print(f"  Adding file: {arcname}")
                        zipf.write(file_path, arcname)

            print(f"✅ Resources compression is completing successfully. ZIP file: {zip_output_file}")

        except Exception as e:
            print(f"❌ Error during resources ZIP compression: {e}")

    else:
        print("Resources folder not found. Skipping ZIP compression step.")

# --- 5. Compress DSL to DSL.DZ using idzip ---
if dsl_conversion_success:
    print("\n" + "="*60)
    print("STEP 4: Compressing DSL file to DSL.DZ format...")
    print("="*60)
    
    idzip_path = "/data/data/com.termux/files/usr/bin/idzip"
    
    if os.path.exists(idzip_path):
        print("idzip found in Termux path. Starting DSL compression...")
        
        try:
            original_size = os.path.getsize(output_file)
            print(f"Original file size: {original_size} bytes")
            
            command = f'{idzip_path} "{output_file}"'
            print(f"Running command: {command}")
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ DSL compression completed successfully!")
                print(f"📁 Compressed file: {output_file}.dz")
                
                if os.path.exists(output_file + ".dz"):
                    compressed_size = os.path.getsize(output_file + ".dz")
                    if original_size > 0:
                        compression_ratio = (1 - compressed_size/original_size) * 100
                        print(f"📊 Compression ratio: {compression_ratio:.1f}%")
                    print("💾 Note: idzip automatically removes the original .dsl file")
                else:
                    print("⚠️ Compressed file was not created successfully")
            else:
                print(f"❌ Error during DSL compression:")
                print(f"Error output: {result.stderr}")
                
        except FileNotFoundError:
            if os.path.exists(output_file + ".dz"):
                print(f"✅ DSL conversion completed successfully!")
                print(f"📁 Final compressed file: {output_file}.dz")
                print("💾 Note: Original .dsl file was automatically removed by idzip")
            else:
                print("⚠️ Original file removed but compressed file not found")
                
        except Exception as e:
            print(f"❌ Error running idzip: {e}")
    else:
        print("⚠️ idzip not found in the specified Termux path.")
        print("Please make sure python-idzip is installed in Termux:")
        print("  pkg install python-idzip")

print("\n" + "="*60)
print("🎉 Process completed successfully!")
print("="*60)
print(f"📊 Statistics:")
print(f"   • Total entries: {len(entries_list)}")
print(f"   • Source language: {source_lang}")
print(f"   • Target language: {target_lang}")
print(f"   • Dictionary name: {dict_name}")
print("="*60)
