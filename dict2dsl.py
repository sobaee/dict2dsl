import io
import os
import re
import subprocess 
from html.parser import HTMLParser
import zipfile 

# --- 1. Dependencies Check ---

def check_command(command):
    """Check if a command is available on the system."""
    try:
        subprocess.check_output([command, '--version'], stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    else:
        return True

if not check_command('pyglossary'):
    print("ERROR: pyglossary is required! Please install it.")
    exit(1)
if not check_command('python3'):
    print("ERROR: python3 is required!")
    exit(1)

# --- 2. Initial Prompt and Skip Logic ---

print("="*60)
print("Dictionary Conversion Tool by Ya Qalb 💖")
print("="*60)

# Prompt to check if input file already exists
skip_pyglossary = input("Do you already have the input file (Tab-separated TXT or MTXT) and want to proceed directly to DSL conversion? (y/n): ").strip().lower()

# Flag to control whether the script should proceed to the main conversion logic
proceed_to_dsl = False

# --- Process Flow based on User Input ---

if skip_pyglossary == 'y':
    # User confirms they have the file and want to proceed directly.
    print("Skipping Pyglossary and proceeding directly to DSL conversion.")
    proceed_to_dsl = True
else:
    # User does NOT have the file, so they must run Pyglossary first.
    
    # --- STEP 1: Run Pyglossary for manual conversion to MTXT ---
    print("\n" + "="*60)
    print("  STEP 1: Run Pyglossary for manual conversion to MTXT")
    print("  (Please convert your source dictionary file manually now)")
    print("="*60)
    
    try:
        subprocess.call('pyglossary --cmd', shell=True)
    except Exception as e:
        print(f"Error running pyglossary: {e}")
        exit(1)

    # --- STEP 2: Ask to Convert TXT/MTXT to DSL (only if pyglossary was run) ---
    print("\n" + "="*60)
    answer = input("STEP 2: Do you want to convert the resulting file to .dsl format? (y/n): ").strip().lower()

    if answer == "y":
        proceed_to_dsl = True

if not proceed_to_dsl:
    print("Conversion to DSL skipped. Exiting.")
    exit(0)

# ========== Get Input File and Metadata ==========

# Get file path
input_file = input("Enter the input file path (e.g., MyDict.txt or MyDict.mtxt): ").strip()
while not os.path.isfile(input_file):
    print("File not found, try again.")
    input_file = input("Enter the input file path: ").strip()

# Defining defaults
dict_name = os.path.splitext(os.path.basename(input_file))[0]
source_lang = ""
target_lang = ""
raw_content_lines = []

# IMPROVED DETECTION VARIABLES
mtxt_header_count = 0
mtxt_separator_found = False
tab_separator_found = False

try:
    with io.open(input_file, "r", encoding="utf-8") as f:
        # Read all lines to analyze structure and parse later
        for i, line in enumerate(f):
            raw_content_lines.append(line)
            
            # --- IMPROVED FILE DETECTION LOGIC ---
            # تم زيادة نطاق البحث إلى 200 سطر لتغطية ملفات pyglossary
            if i < 200:
                stripped_line = line.strip()
                
                # 1. Count MTXT header lines (e.g., ##name, ##sourceLang)
                if stripped_line.startswith("##"):
                    mtxt_header_count += 1
                
                # 2. Check for the mandatory MTXT entry separator (</>)
                if "</>" in stripped_line:
                    mtxt_separator_found = True
                
                # 3. Check for Tab separator (TXT format) - يجب أن لا يكون سطر رأس MTXT
                if "\t" in line and not line.startswith("##"):
                    tab_separator_found = True
                    
except Exception as e:
    print(f"❌ Error reading input file: {e}")
    exit(1)

# FINAL DECISION: Improved file type detection
file_extension = input_file.lower()

if file_extension.endswith('.mtxt'):
    # إذا كان الامتداد .mtxt، نثق به ونعتبره MTXT
    is_mtxt = True
    print("File extension is .mtxt - processing as MTXT format")
elif file_extension.endswith('.txt'):
    # إذا كان الامتداد .txt: نعتمد على وجود فاصل الإدخال </>
    # هذا يحل مشكلة الرؤوس المتبقية من pyglossary التي لا تجعل الملف MTXT بالضرورة
    if mtxt_separator_found:
        is_mtxt = True
        print("File extension is .txt but content appears to be MTXT format (</> found)")
    else:
        is_mtxt = False
        print("File extension is .txt - processing as Tab-separated TXT format (No </> found)")
else:
    # للامتدادات الأخرى: الاعتماد على وجود فاصل الإدخال </> كأولوية
    if mtxt_separator_found:
        is_mtxt = True
        print("Detected MTXT format based on content (</> found)")
    elif tab_separator_found:
        is_mtxt = False
        print("Detected Tab-separated TXT format based on content (No </> but Tab found)")
    else:
        # Default fallback - ask user
        print("⚠️  Could not auto-detect file format")
        user_choice = input("Is this file MTXT format? (y/n): ").strip().lower()
        is_mtxt = (user_choice == 'y')
         
# --- Conditional Parsing ---

entries_list = []

if is_mtxt:
    print("Processing as MTXT format...")
    
    # 1. Extract metadata and process content lines
    content_lines = []
    for line in raw_content_lines:
        stripped = line.strip()
        
        # Parse headers
        if stripped.startswith("##name"):
            dict_name = stripped.split("\t", 1)[1].strip()
        elif stripped.startswith("##sourceLang"):
            source_lang = stripped.split("\t", 1)[1].strip()
        elif stripped.startswith("##targetLang"):
            target_lang = stripped.split("\t", 1)[1].strip()
        elif stripped.startswith("##"):
            continue # تجاهل باقي الرؤوس
        else:
            # MTXT often has literal \n which needs removal
            clean_line = line.replace("\\n", "")
            content_lines.append(clean_line.rstrip("\n"))
            
    # 2. Split entries by </> and handle links (MTXT structure)
    raw = "\n".join(content_lines)
    blocks = [b.strip() for b in raw.split("</>") if b.strip()]

    # NEW: تجميع كل المداخل لنفس الكلمة الرئيسية
    headword_entries = {}
    links_to_process = {}  # لتخزين الروابط بشكل منفصل
    
    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
            
        headword = lines[0]  # الكلمة الرئيسية
        
        # التحقق إذا كان هذا مدخل رابط (@@@LINK=)
        if len(lines) >= 2 and lines[1].startswith("@@@LINK="):
            target = lines[1].replace("@@@LINK=", "").strip()
            links_to_process[headword] = target
            continue
        
        # إذا كانت هذه الكلمة موجودة مسبقاً، نضيف المحتوى الجديد إليها
        if headword in headword_entries:
            # دمج المحتوى مع المحتوى السابق
            existing_content = headword_entries[headword]
            new_content = "\n".join(lines[1:])
            
            # إضافة فاصل بين التعريفات المختلفة لنفس الكلمة
            if existing_content and new_content:
                headword_entries[headword] = existing_content + "\n[m1]\\ [/m]\n" + new_content
            elif new_content:
                headword_entries[headword] = existing_content + new_content
        else:
            # أول مدخل لهذه الكلمة
            headword_entries[headword] = "\n".join(lines[1:])

    # NEW: تجميع الكلمات المرتبطة
    word_groups = {}
    
    # أولاً: إضافة كل الكلمات الرئيسية التي لديها محتوى
    for headword in headword_entries:
        word_groups[headword] = [headword]
        
    # ثانياً: معالجة الروابط وإضافتها للمجموعات المناسبة
    for linked_word, main_word in links_to_process.items():
        if main_word in word_groups:
            word_groups[main_word].append(linked_word)
        else:
            # إذا لم توجد الكلمة الرئيسية، ننشئ مجموعة جديدة
            word_groups[main_word] = [main_word, linked_word]
            # نضيف مدخل فارغ للكلمة الرئيسية
            headword_entries[main_word] = ""

    # 4. تحويل إلى تنسيق entries_list
    for main_head, all_headwords in word_groups.items():
        html_content = headword_entries.get(main_head, "")
        if html_content or all_headwords:
            entries_list.append({
                'headwords': all_headwords,
                'html': html_content
            })
            
    # --- Prompt for languages if not found in MTXT headers ---
    if not source_lang:
        source_lang = input(f"Enter Source Language (e.g., ENGLISH): ").strip().upper() or "ENGLISH"
    if not target_lang:
        target_lang = input(f"Enter Target Language (e.g., ARABIC): ").strip().upper() or "ARABIC"
            
else:
    print("Processing as Tab-separated TXT format...")
    
    # NEW: تجميع المداخل لنفس الكلمة الرئيسية في ملفات TXT أيضاً
    headword_entries = {}
    
    for line in raw_content_lines:
        line = line.strip()
        if not line:
            continue
        
        # تخطي أسطر الرؤوس (##)
        if line.startswith("##"):
            continue
            
        # Split line by the first Tab character
        parts = line.split("\t", 1)
        
        if len(parts) != 2:
            continue
            
        head = parts[0].strip()
        html = parts[1].strip()
        
        # Split headwords by '|'
        headwords = [h.strip() for h in head.split("|") if h.strip()]
        
        if headwords and html:
            # استخدام أول headword كمفتاح للتجميع
            main_headword = headwords[0]
            
            if main_headword in headword_entries:
                # دمج المحتوى مع المحتوى السابق
                existing_content = headword_entries[main_headword]['html']
                existing_headwords = headword_entries[main_headword]['headwords']
                
                # إضافة أي headwords جديدة
                for hw in headwords:
                    if hw not in existing_headwords:
                        existing_headwords.append(hw)
                
                # دمج المحتوى مع فاصل
                headword_entries[main_headword]['html'] = existing_content + "\n[m1]\\ [/m]\n" + html
            else:
                # أول مدخل لهذه الكلمة
                headword_entries[main_headword] = {
                    'headwords': headwords,
                    'html': html
                }

    # تحويل إلى entries_list
    for entry_data in headword_entries.values():
        entries_list.append(entry_data)

    # Since Tab-TXT doesn't have headers, prompt user for languages
    if not source_lang:
        source_lang = input(f"Enter Source Language (e.g., ENGLISH): ").strip().upper() or "ENGLISH"
    if not target_lang:
        target_lang = input(f"Enter Target Language (e.g., ARABIC): ").strip().upper() or "ARABIC"


print(f"✅ Successfully loaded {len(entries_list)} entries.")

# Defining the output DSL file name
output_file = dict_name + ".dsl"
print(f"Output DSL will be: {output_file}")


# ========== Fix phonetic brackets only for pronunciation (No change) ==========
def fix_phonetic_brackets(text):
    dsl_codes = ["m1", "b", "i", "u", "c", "s", "/m", "/b", "/i", "/u", "/c", "/s"]

    def repl(m):
        inner = m.group(1).strip()
        for code in dsl_codes:
            if inner.startswith(code):
                return f"[{inner}]"
        return "{" + inner + "}"

    return re.sub(r"\[([^\]]+)\]", repl, text)

# ========== HTML Parser (Updated with sound link conversion) ==========
class LingvoHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = ""
        self.stack = []
        self.paragraph_started = False 
    
    def emit(self, text):
        self.output += text

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self.stack.append((tag, attrs_dict))

        if tag in ["object", "img"]:
            file_attr = attrs_dict.get("data") or attrs_dict.get("src")
            if file_attr:
                self.emit(f"[s]{file_attr}[/s]")

        elif tag == "br":
            self.emit("\n\t")

        elif tag == "p":
            if self.paragraph_started:
                # الفاصل القوي للسطر الفارغ: \n\t[m1]\ [/m]\n\t
                self.emit("\n\t[m1]\\ [/m]\n\t") 
            self.paragraph_started = True

        elif tag == "font":
            color = attrs_dict.get("color")
            if color:
                clean = color.lstrip("#")
                self.emit(f"[c {clean}]")

        elif tag == "strong":
            # Using strong for major division inside a definition
            self.emit("[/m]\n\t[m1]")

        elif tag == "b":
            self.emit("[b]")
        
        elif tag == "i":
            self.emit("[i]")

        elif tag == "u":
            self.emit("[u]")

        elif tag == "s":
            self.emit("[s]")
            
        elif tag == "a":
            # تحويل روابط الصوت sound://
            href = attrs_dict.get("href", "")
            if href.startswith("sound://"):
                # إزالة sound:// من البداية
                sound_file = href[8:]
                # تحويل إلى تنسيق DSL: [m1][s]filename.ogg[/s][/m]
                self.emit(f"[m1][s]{sound_file}[/s][/m]")
    
    def handle_endtag(self, tag):
        if tag == "font":
            for i in range(len(self.stack)-1, -1, -1):
                stack_tag, attrs_dict = self.stack[i]
                if stack_tag == "font":
                    color = attrs_dict.get("color")
                    if color:
                        self.emit("[/c]")
                    break
        
        elif tag == "p":
            # فاصل سطر بسيط بعد نهاية الفقرة
            self.emit("\n\t") 

        elif tag == "b":
            self.emit("[/b]")

        elif tag == "i":
            self.emit("[/i]")

        elif tag == "u":
            self.emit("[/u]")

        elif tag == "s":
            self.emit("[/s]")

        elif tag == "strong":
            self.emit("")
            
        elif tag == "a":
            # لا نضيف أي شيء عند إغلاق رابط الصوت
            pass
    
    def handle_data(self, data):
        self.emit(data)
    
    def close(self):
        super().close()
        return self.output

# ========== Write DSL ==========
try:
    with io.open(output_file, "w", encoding="utf-16") as out:
        out.write(f'#NAME "{dict_name}"\n')
        out.write(f'#INDEX_LANGUAGE "{source_lang}"\n')
        out.write(f'#CONTENTS_LANGUAGE "{target_lang}"\n\n')

        # Iterate over the standardized entries list
        for entry in entries_list:
            headwords = entry['headwords']
            html_block = entry['html']

            # 1. Write all headwords/aliases
            for w in headwords:
                out.write(w + "\n")

            # If there is no content (link-only entries in MTXT), write an empty m1
            if not html_block:
                out.write("\t[m1][/m]\n")
                continue

            # 2. Parse HTML content
            parser = LingvoHTMLParser()
            parser.feed(html_block)
            parsed = parser.close()

            # 3. Apply phonetic fix
            parsed = fix_phonetic_brackets(parsed)

            # 4. Cleanup and formatting
            
            # Remove repeated hard paragraph breaks
            parsed = re.sub(
                r"(\n\t\[m1\]\\ \[/m\]\n\t\s*){2,}",
                "\n\t[m1]\\ [/m]\n\t",
                parsed
            )
            
            # Remove excessive line breaks and tabs
            parsed = re.sub(r"(\n\t){2,}", "\n\t", parsed)
            parsed = re.sub(r"(\n\s*){2,}", "\n", parsed).strip()

            # Ensure every output line in DSL starts with a tab
# INCLUDING lines coming directly from MTXT/TXT before HTML parsing
# Ensure all lines start with a tab and apply [m1] where needed
# Ensure every output line in DSL starts with a tab
            lines = parsed.split("\n")
            final_lines = []

            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue

                # السطر المخصص للفاصل
                if ln == "[m1]\\ [/m]":
                    final_lines.append("\t" + ln)
                    continue

                # إذا السطر لا يحتوي [m..] نضيفه
                if not ln.startswith("[m"):
                    final_lines.append("\t[m1]" + ln + "[/m]")
                else:
                    final_lines.append("\t" + ln)

            parsed = "\n".join(final_lines)

            out.write(parsed + "\n")

    print("\n✅ DSL conversion completed successfully.")
    
    dsl_conversion_success = True

except Exception as e:
    print(f"❌ Error during DSL conversion: {e}")
    dsl_conversion_success = False


# --- 4. ZIP Resources ---

if dsl_conversion_success:
    print("\n" + "="*60)
    print("STEP 3: Checking for resources folder and compressing it...")
    print("="*60)
    
    # We assume the resource folder name is based on the input file name
    res_folder_path = input_file + "_res"

    print(f"Searching for resources folder: {res_folder_path}")

    if os.path.isdir(res_folder_path):
        # The zip file name is based on the DSL output name (MyDict.files.dsl.zip)
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

            print(f"✅ Resources compression completed successfully. ZIP file created: {zip_output_file}")

        except Exception as e:
            print(f"❌ Error during resources ZIP compression: {e}")

    else:
        print("Resources folder not found. Skipping ZIP compression step.")

# --- 5. Compress DSL to DSL.DZ using idzip ---
if dsl_conversion_success:
    print("\n" + "="*60)
    print("STEP 4: Compressing DSL file to DSL.DZ format...")
    print("="*60)
    
    # استخدام المسار المحدد لـ idzip في Termux
    idzip_path = "/data/data/com.termux/files/usr/bin/idzip"
    
    if os.path.exists(idzip_path):
        print("idzip found in Termux path. Starting DSL compression...")
        
        try:
            # حفظ حجم الملف الأصلي قبل الضغط
            original_size = os.path.getsize(output_file)
            print(f"Original file size: {original_size} bytes")
            
            # Run idzip command with full path
            command = f'{idzip_path} "{output_file}"'
            print(f"Running command: {command}")
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ DSL compression completed successfully!")
                print(f"📁 Compressed file: {output_file}.dz")
                
                # Check if the compressed file was created
                if os.path.exists(output_file + ".dz"):
                    compressed_size = os.path.getsize(output_file + ".dz")
                    compression_ratio = (1 - compressed_size/original_size) * 100
                    print(f"📊 Compression ratio: {compression_ratio:.1f}%")
                    print(f"💾 Note: idzip automatically removes the original .dsl file")
                else:
                    print("⚠️ Compressed file was not created successfully")
            else:
                print(f"❌ Error during DSL compression:")
                print(f"Error output: {result.stderr}")
                
        except FileNotFoundError:
            # هذا طبيعي لأن idzip يحذف الملف الأصلي
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