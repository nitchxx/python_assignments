
from pathlib import Path
import os
import stat
import hashlib
import shutil
import logging
from collections import Counter
from datetime import datetime


# =====================================
# STAGE 8: LOGGING CONFIGURATION
# =====================================

logging.basicConfig(
    filename="organizer.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

logging.info("File Organizer program started")


# =====================================
# FUNCTION: GENERATE UNIQUE DESTINATION
# =====================================

def get_unique_destination(folder, file_path, planned_destinations):

    destination = folder / file_path.name

    counter = 1

    while (
        destination.exists()
        or destination.resolve() in planned_destinations
    ):

        new_name = (
            f"{file_path.stem}_{counter}{file_path.suffix}"
        )

        destination = folder / new_name
        counter += 1

    planned_destinations.add(destination.resolve())

    return destination


# =====================================
# FUNCTION: CALCULATE FILE HASH
# =====================================

def calculate_hash(file_path):

    file_hash = hashlib.sha256()

    with open(file_path, "rb") as source_file:

        while True:

            content = source_file.read(1024 * 1024)

            if not content:
                break

            file_hash.update(content)

    return file_hash.hexdigest()


# =====================================
# FUNCTION: CHECK HIDDEN / SYSTEM FILES
# =====================================

def is_hidden_or_system(file_path):

    if file_path.name.startswith("."):
        return True

    file_attributes = file_path.stat().st_file_attributes if hasattr(
        file_path.stat(), "st_file_attributes"
    ) else 0

    hidden_flag = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0)
    system_flag = getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0)

    if file_attributes & hidden_flag:
        return True

    if file_attributes & system_flag:
        return True

    return False


# =====================================
# FUNCTION: MOVE WITHOUT OVERWRITING
# =====================================

def safe_move(source, destination):

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if destination.exists():
        raise FileExistsError(
            f"Destination already exists: {destination}"
        )

    # Copy using exclusive creation.
    # 'xb' prevents overwriting an existing file.

    try:

        with open(source, "rb") as source_file:

            with open(destination, "xb") as destination_file:

                shutil.copyfileobj(
                    source_file,
                    destination_file
                )

        shutil.copystat(source, destination)

        # Remove original only after successful copying.

        source.unlink()

    except Exception:

        if destination.exists():
            destination.unlink()

        raise


# =====================================
# MAIN PROGRAM
# =====================================

path_details = input("Enter a path: ")

try:

    if not path_details.strip():

        raise ValueError("Path cannot be empty")

    path_input = Path(path_details).resolve()

    if not path_input.exists():

        raise FileNotFoundError("Directory does not exist")

    elif path_input.is_file():

        raise NotADirectoryError(
            "The given path is a file, not a directory"
        )

    elif path_input.is_dir():

        print("Directory exists!")

        logging.info(
            "Directory validation successful: %s",
            path_input
        )

    # =====================================
    # FILE CATEGORIES
    # =====================================

    file_categories = {

        "Documents": [".pdf", ".docx", ".doc", ".txt"],

        "Images": [".jpg", ".jpeg", ".png", ".gif"],

        "Audio": [".mp3", ".wav", ".aac"],

        "Videos": [".mp4", ".mkv", ".avi"],

        "Code": [".py", ".js", ".html", ".css"],

        "Spreadsheets": [".xlsx", ".xls", ".csv"]
    }

    # =====================================
    # STATISTICS
    # =====================================

    duplicate_find = {}

    category_count = Counter()

    total_size = 0
    total_files_scanned = 0
    total_folders = 0

    hidden_count = 0
    duplicate_count = 0

    moved_files = 0
    skipped_files = 0

    failed_files = 0

    planned_movements = []

    planned_destinations = set()

    # =====================================
    # STAGE 6: DRY-RUN SETTINGS
    # =====================================

    while True:

        dry_input = input(
            "\nEnable dry-run mode? (yes/no): "
        ).strip().lower()

        if dry_input == "yes":

            dry_run = True
            break

        elif dry_input == "no":

            dry_run = False
            break

        else:

            print("Enter yes or no.")

    # =====================================
    # DIRECTORY SCANNING
    # =====================================

    logging.info("Starting directory scanning")

    # Exclude folders created by this organizer.

    excluded_folders = (
        list(file_categories.keys())
        + ["Others", "Duplicates"]
    )

    def scan_error(error):

        nonlocal_dummy = error

        logging.error(
            "Directory scanning error: %s",
            nonlocal_dummy
        )

    for root, dirs, files in os.walk(
        path_input,
        topdown=True,
        onerror=scan_error
    ):

        # Ignore hidden/system directories
        # and organizer-created folders.

        valid_dirs = []

        for folder in dirs:

            folder_path = Path(root) / folder

            try:

                if folder in excluded_folders:
                    continue

                if is_hidden_or_system(folder_path):
                    continue

                valid_dirs.append(folder)

            except OSError:

                failed_files += 1

                logging.exception(
                    "Unable to inspect directory: %s",
                    folder_path
                )

        dirs[:] = valid_dirs

        total_folders += len(dirs)

        # =====================================
        # PROCESS EACH FILE
        # =====================================

        for file in files:

            join_input = Path(root) / file

            try:

                if not join_input.is_file():
                    continue

                if join_input.is_symlink():
                    continue

                if is_hidden_or_system(join_input):

                    hidden_count += 1

                    logging.info(
                        "Hidden/system file ignored: %s",
                        join_input
                    )

                    continue

                # Ignore previously generated program files.

                if join_input.name in [
                    "organizer.log",
                    "organizer_report.txt"
                ]:

                    continue

                total_files_scanned += 1

                extension = join_input.suffix.lower()

                file_size = join_input.stat().st_size

                total_size += file_size

                file_size_kb = file_size / 1024

                # =====================================
                # CATEGORY IDENTIFICATION
                # =====================================

                category = "Others"

                for category_name, extensions in file_categories.items():

                    if extension in extensions:

                        category = category_name
                        break

                category_count[category] += 1

                print("\nFile:", file)
                print("Extension:", extension)
                print("File Size:", round(file_size_kb, 2), "KB")
                print("Category:", category)

                # =====================================
                # DUPLICATE DETECTION
                # =====================================

                file_hash = calculate_hash(join_input)

                is_duplicate = file_hash in duplicate_find

                if not is_duplicate:

                    duplicate_find[file_hash] = str(join_input)

                    new_folder = path_input / category

                else:

                    duplicate_count += 1

                    new_folder = path_input / "Duplicates"

                    logging.warning(
                        "Duplicate detected: %s | Original: %s",
                        join_input,
                        duplicate_find[file_hash]
                    )

                    print("Duplicate file detected!")

                # =====================================
                # DESTINATION GENERATION
                # =====================================

                destination = get_unique_destination(
                    new_folder,
                    join_input,
                    planned_destinations
                )

                # Already organized files do not need moving.

                if join_input.resolve() == destination.resolve():

                    continue

                planned_movements.append(
                    (join_input, destination)
                )

                print("Destination:", destination)

            except PermissionError:

                failed_files += 1

                logging.exception(
                    "Permission denied while scanning: %s",
                    join_input
                )

                print("Permission denied:", join_input)

            except OSError:

                failed_files += 1

                logging.exception(
                    "File scanning failed: %s",
                    join_input
                )

                print("Unable to process:", join_input)

            except Exception:

                failed_files += 1

                logging.exception(
                    "Unexpected scanning error: %s",
                    join_input
                )

                print("Unexpected error:", join_input)

    logging.info("Directory scanning completed")

    logging.info(
        "Total files scanned: %d",
        total_files_scanned
    )

    # =====================================
    # DUPLICATE REPORT
    # =====================================

    print("\n========== DUPLICATE REPORT ==========")

    if duplicate_count > 0:

        print("Duplicate files found:", duplicate_count)

    else:

        print("No duplicate files found.")

    # =====================================
    # STAGE 6: DRY-RUN PREVIEW
    # =====================================

    print("\n========== FILE ORGANIZER ==========")

    if dry_run:

        print("\nDRY-RUN MODE ENABLED")

    else:

        print("\nACTUAL MOVEMENT MODE")

    print("\nPlanned movements:\n")

    for index, (source, destination) in enumerate(
        planned_movements,
        start=1
    ):

        print(
            f"{index}. {source} -> {destination}"
        )

    total_planned = len(planned_movements)

    print("\nTotal files scanned:", total_files_scanned)

    print("Total planned movements:", total_planned)

    # =====================================
    # USER CONFIRMATION
    # =====================================

    while True:

        user_confirmation = input(
            "\nDo you want to continue? (yes/no): "
        ).strip().lower()

        if user_confirmation == "yes":

            print("\nUser approved the operation.")

            logging.info(
                "User approved file organization"
            )

            if dry_run:

                print("\nDry-run mode is enabled.")

                print("No files were moved.")

                skipped_files = total_planned

                logging.info(
                    "Dry-run enabled; no files moved"
                )

            else:

                # =====================================
                # ACTUAL FILE MOVEMENT
                # =====================================

                for source, destination in planned_movements:

                    try:

                        safe_move(source, destination)

                        moved_files += 1

                        print("Moved to:", destination)

                        logging.info(
                            "Successfully moved: %s -> %s",
                            source,
                            destination
                        )

                    except PermissionError:

                        failed_files += 1

                        print(
                            "Permission denied:",
                            source
                        )

                        logging.exception(
                            "Permission denied while moving: %s",
                            source
                        )

                    except FileExistsError:

                        failed_files += 1

                        print(
                            "Destination already exists:",
                            destination
                        )

                        logging.exception(
                            "Destination conflict: %s",
                            destination
                        )

                    except OSError:

                        failed_files += 1

                        print(
                            "Unable to move:",
                            source
                        )

                        logging.exception(
                            "File movement failed: %s",
                            source
                        )

                    except Exception:

                        failed_files += 1

                        print(
                            "Unexpected error while moving:",
                            source
                        )

                        logging.exception(
                            "Unexpected movement error: %s",
                            source
                        )

                print("\nFile organization completed!")

            break

        elif user_confirmation == "no":

            print("\nOperation cancelled.")

            print("No files were moved.")

            skipped_files = total_planned

            logging.warning(
                "User cancelled file organization"
            )

            break

        else:

            print(
                "Invalid input. Please enter yes or no."
            )

            logging.warning(
                "Invalid confirmation input"
            )

    # =====================================
    # STAGE 7: REPORT GENERATION
    # =====================================

    report_date = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    total_size_mb = total_size / (1024 * 1024)

    # Avoid overwriting an existing report.

    report_path = path_input / "organizer_report.txt"

    report_counter = 1

    while report_path.exists():

        report_path = path_input / (
            f"organizer_report_{report_counter}.txt"
        )

        report_counter += 1

    report = f"""
========================================
          FILE ORGANIZER REPORT
========================================

Report Date: {report_date}

DIRECTORY INFORMATION
----------------------------------------
Directory Path       : {path_input}
Total Files Scanned  : {total_files_scanned}
Total Folders        : {total_folders}

FILE CATEGORY SUMMARY
----------------------------------------
"""

    for category, count in sorted(category_count.items()):

        report += f"{category:<20}: {count:>5}\n"

    report += f"""
FILE STATISTICS
----------------------------------------
Total Size           : {total_size_mb:.2f} MB
Hidden Files Ignored : {hidden_count}
Duplicate Files      : {duplicate_count}

ORGANIZATION SUMMARY
----------------------------------------
Planned Files        : {total_planned}
Successfully Moved   : {moved_files}
Skipped Files        : {skipped_files}
Failed Files         : {failed_files}

MODE
----------------------------------------
Dry-run Enabled      : {dry_run}

========================================
             END OF REPORT
========================================
"""

    try:

        with open(
            report_path,
            "x",
            encoding="utf-8"
        ) as report_file:

            report_file.write(report)

        print("\nReport generated successfully!")

        print("File:", report_path)

        logging.info(
            "Report generated successfully: %s",
            report_path
        )

    except OSError:

        print("\nReport generation failed.")

        logging.exception(
            "Report generation failed"
        )

except ValueError as error:

    print("Error:", error)

    logging.error(
        "Input validation error: %s",
        error
    )

except FileNotFoundError as error:

    print("Error:", error)

    logging.error(
        "Directory not found: %s",
        error
    )

except NotADirectoryError as error:

    print("Error:", error)

    logging.error(
        "Invalid directory: %s",
        error
    )

except PermissionError:

    print("Permission denied.")

    logging.exception(
        "Permission error"
    )

except OSError:

    print("Unexpected operating system error.")

    logging.exception(
        "Unexpected operating system error"
    )

except Exception:

    print("An unexpected error occurred.")

    logging.exception(
        "Unexpected program error"
    )

finally:

    logging.info(
        "File Organizer program execution finished"
    )

    print("\nProgram execution finished.")
