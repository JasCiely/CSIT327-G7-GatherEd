import sys
import os

file_path = r"c:\Users\Raymart Ruperez\Desktop\New folder\GatherED\CSIT327-G7-GatherEd\apps\student_dashboard_page\templates\fragments\my_events\my_events_content.html"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)

print(f"Read {len(lines)} lines.")
sys.stdout.flush()

new_lines = []
i = 0
found = False
while i < len(lines):
    line = lines[i]
    # Check for the anchor tag
    if 'href="{% url \'event_list\' %}"' in line:
        print(f"Potential match at line {i+1}: {line.strip()}")
        sys.stdout.flush()
        if i + 2 < len(lines):
            # print(f"Next line: {lines[i+1].strip()}")
            # print(f"Next next line: {lines[i+2].strip()}")
            if 'Register Again' in lines[i+1] and '</a>' in lines[i+2]:
                print("Confirmed match.")
                indent = line[:line.find('<')]
                new_lines.append(indent + '<button class="btn btn-secondary btn-sm" disabled>\n')
                new_lines.append(indent + '    <i class="fas fa-info-circle"></i> Cancelled\n')
                new_lines.append(indent + '</button>\n')
                i += 3
                found = True
                continue
    
    new_lines.append(line)
    i += 1

if found:
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("Successfully updated the file.")
    except Exception as e:
        print(f"Error writing file: {e}")
else:
    print("Could not find the target block.")
