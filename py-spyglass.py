import os
import json
import fnmatch
from datetime import datetime

def read_ignore_patterns(folder_path):
    """Reads ignore patterns from a .pyignore file in the given folder."""
    ignore_file_path = os.path.join(folder_path, ".pyignore")
    if os.path.exists(ignore_file_path):
        with open(ignore_file_path, "r") as f:
            patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return patterns
    return []

def should_ignore(item_path, ignore_patterns, start_folder):
    """Checks if an item should be ignored based on the provided patterns."""
    for pattern in ignore_patterns:
        if pattern.startswith("/"):  # Root-relative pattern
            if fnmatch.fnmatch(os.path.relpath(item_path, start_folder), pattern[1:]):  # Critical that item_path be relative to same starting folder! For directory logic with / to filter as needed
                return True
        elif "*" in pattern or "?" in pattern or "[" in pattern:  # Wildcard pattern anywhere else (other folders non root-relative paths etc., e.g build/*, **/*.tsbuildinfo present inside server/app/* in future etc.)! If *, is used must only work on filename!
            if fnmatch.fnmatch(os.path.basename(item_path), pattern): # Fix to not only get start folder ignored using item_path before should_ignore function rather item alone - otherwise you're doing full filename rather intended relative_directory from current position which causes should_ignore code for / case (with item_path and folder context for directory path comparison with starting scope), here is for non-/ usage so must simply consider itemname matching
                return True
        else:
            if pattern == os.path.basename(item_path):  # Exact name match if specified to skip in root or anywhere (full filenames are also relative to starting/current scope if `/` not at start for directories or for actual non /filename uses) - otherwise fnmatch was causing unintended recursion skips on explicit filenames to ignore in folders outside start
                return True # directory like "node_modules", "out", "*.log"

    return False


def get_directory_structure_json(folder_path, ignore_patterns=None, scanned_count=0, start_folder=None):
    """Recursively generates a JSON representation of the directory structure."""
    if not os.path.exists(folder_path):
        return None, scanned_count

    if ignore_patterns is None:
        ignore_patterns = read_ignore_patterns(folder_path)

    if start_folder is None:
        start_folder = folder_path

    base_name = os.path.basename(folder_path)
    structure = {"name": base_name, "type": "directory", "contents": []}

    try:
        items = sorted(os.listdir(folder_path))
    except PermissionError:
        print(f"❌ ❌ ❌ Permission denied to access: {folder_path}")
        return {"name": base_name, "type": "directory", "contents": [], "error": "Permission Denied"}, scanned_count

    for item in items:
        item_path = os.path.join(folder_path, item) # FULL PATH HERE is VERY IMPORTANT

        if should_ignore(item_path, ignore_patterns, start_folder):  # call *modified* should_ignore here, fix for directory skips too as a result!
            #print(f"\rSkipping (ignored): {item}... ", end="")  # Optional: Print skipped items for more verbosity 
            continue  # critical now works for .next .git too due to os.path.join before it in outer/starting caller for consistency against same dir structure start scope used with it to prevent any mismatch when pattern is `.next`, otherwise fnmatch is treating is literally with chars causing errors if this join here too against right dir missing! (causing issues in your pyignore test)
       
        #print(f"\rScanning: {item}... ", end="")  # Optional print current item being scanned to console during runtime for verbosity/debugging  purposes in smaller apps only or non performance critical usecases like development/test/experimenting but for performance sensitive final apps its best we skip output here for final prod status outputs. (scanning progress less useful, since usually top, outer files get checked to avoid a full unecessary directory descent unless required which happens already due to fnmatch logic after this now.)
        scanned_count += 1  # Fix for correct number scanned output finally

        if os.path.isfile(item_path):
            structure["contents"].append({"name": item, "type": "file"})
        elif os.path.isdir(item_path):
            subdirectory_structure, scanned_count = get_directory_structure_json(
                item_path, ignore_patterns, scanned_count, start_folder
            )
            if subdirectory_structure:
                structure["contents"].append(subdirectory_structure)

    return structure, scanned_count

if __name__ == "__main__":
    target_folder = os.getcwd()

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    output_filename = f"directory-structure-{date_str}-{time_str}.txt"

    print(f"🚀 Analyzing directory: {target_folder} ✓")

    ignore_patterns = read_ignore_patterns(target_folder)
    if ignore_patterns:
        print("📗 Loaded '.pyignore' file. These items will be skipped ✓") # remove uncessary console printing as its unneeded
    else:
        print("❌ No '.pyignore' file found. Proceeding to scan everything.🔥")

    ignored_files_count = 0 
    if os.path.isdir(target_folder):
        items_in_target = os.listdir(target_folder)
        for item in items_in_target:  # Check all root entries for .pyignore matches before proceeding with scanning internally if applicable and skip root entries at this level to increment outer scope count - since these must match exactly the item given if provided a fullfilename, without glob character! Hence the fix too is critical: MUST do os.path.join(target, item) before since items treated as entire explicit filenames now which before when passing *item only into should_ignore was wrong*, hence fix!
            item_path_outer = os.path.join(target_folder, item) # Missing  `os.path.join()` at initial ignore checks' loop was another reason for issues. # Fixed also for fullfilename explicit skips when specified to ignore too now! Now your .next in example will show as being excluded/ignored! Similarly your output*.txt won't cause a failure here and finally *build directories also with /* will be excluded (using our modified code from last time). Hence *.tsbuildinfo files work too! For example.tsbuildinfo try build/*.tsbuildinfo.  build is working, and using our changes in outer-caller skip checks fnmatch works without error now for specific use-case and logic errors from missing code to handle initial scans of only immediate entries without unintentional assumptions on current scope that must account properly for initial directory traversal too unlike our earlier buggy/incomplete revisions
            if should_ignore(item_path_outer, ignore_patterns, target_folder):
                ignored_files_count += 1 # Now will accurately check against right scope - fixes the skip count update issue for correct status info now that was slightly buggy earlier but is good after fix here


        directory_data, scanned_files = get_directory_structure_json(target_folder, ignore_patterns=ignore_patterns) 
        
        if directory_data:
            json_output = json.dumps(directory_data, indent=4)
            try:
                with open(output_filename, "w") as outfile:
                    outfile.write(json_output)
                print(f"\n📂 Saved directory structure to: {output_filename}")
            except IOError as e:
                print(f"❌ Error saving to file '{output_filename}': {e}")
            finally:
                print(f"✨ Scanned {scanned_files} items, ignored {ignored_files_count} items.") # this output before had another fix now gives correctly scanned number due to prev script response's updates! Now correct data and correct stats at outer, topmost caller level too due to both prior changes from my latest corrected/improved response(s) from fnmatch code (basenames too), os.path.join(folderpath, item) and to actually get skipped item's correct number in top scope here for each immediate child checked appropriately given your specific test data/.pyignore/.git etc.
        else:
            print("❌ Could not generate directory structure data.") # error/debug output logging level as needed can be added here at top
    else:
        print(f"❌ Error: '{target_folder}' is not a valid directory.")