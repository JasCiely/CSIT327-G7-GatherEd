import os

file_path = r"c:\Users\Raymart Ruperez\Desktop\New folder\GatherED\CSIT327-G7-GatherEd\apps\student_dashboard_page\templates\fragments\my_events\my_events_content.html"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
found = False

target_start = "$title.text(title);"
target_end = "$iconContainer.append('<i class=\"fas fa-times-circle error-icon\"></i>');"

while i < len(lines):
    line = lines[i]
    if target_start in line:
        # Found the start
        print(f"Found start at line {i+1}")
        # Check if the block matches roughly what we expect
        # We'll just replace the lines from here until the end of the if/else block
        
        # Construct the new block
        indent = line[:line.find('$')]
        new_lines.append(indent + "$title.text(title);\n")
        new_lines.append(indent + "if (isSuccess) {\n")
        new_lines.append(indent + "     $title.append(' 🎉');\n")
        new_lines.append(indent + "}\n\n")
        new_lines.append(indent + "$message.text(message);\n")
        new_lines.append(indent + "$subtext.text(subtext || '');\n\n")
        new_lines.append(indent + "$iconContainer.html('');\n")
        new_lines.append(indent + "if (isSuccess) {\n")
        new_lines.append(indent + "    $iconContainer.append('<i class=\"fas fa-check success-icon\"></i>');\n")
        new_lines.append(indent + "} else {\n")
        new_lines.append(indent + "    $iconContainer.append('<i class=\"fas fa-times error-icon\"></i>');\n")
        new_lines.append(indent + "}\n")
        
        # Skip lines until we pass the original block
        # The original block ends with the else branch closing brace
        # Let's just skip a fixed number of lines or look for the closing brace of the else
        
        # Original block:
        # $title.text(title);
        # $message.text(message);
        # $subtext.text(subtext || '');
        # 
        # $iconContainer.html('');
        # if (isSuccess) {
        #     $iconContainer.append('<i class="fas fa-check-circle success-icon"></i>');
        # } else {
        #     $iconContainer.append('<i class="fas fa-times-circle error-icon"></i>');
        # }
        
        # That is roughly 10 lines.
        # Let's skip until we see the closing brace of the else block
        
        j = i
        while j < len(lines):
            if "error-icon" in lines[j]:
                # This is the line inside the else
                # The next line should be '}'
                j += 1 # Skip the line with error-icon
                if '}' in lines[j]:
                    j += 1 # Skip the closing brace
                break
            j += 1
        
        i = j
        found = True
        continue

    new_lines.append(line)
    i += 1

if found:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Successfully updated the file.")
else:
    print("Could not find the target block.")
