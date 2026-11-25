from pathlib import Path
import os
import stat

path_details = input("Enter a path :")

try :

 if not path_details.strip():
   raise ValueError("path cannot be empty")

 path_input = Path(path_details)
 
 if not path_input.exists():
   raise FileNotFoundError("directory does not exist")
 elif  path_input.is_file():
   raise NotADirectoryError("The given path is a file, not a directory")
 elif path_input.is_dir():
        print("Directory exists!")

 for root, dirs, files in os.walk(path_input):
   for file in files:
        extension = os.path.splitext(file)[1]

        join_input = os.path.join(root,file)

        file_size = os.path.getsize(join_input)

        file_size_kb = file_size / 1024

        hidden=""
        file_attributes = os.stat(join_input).st_file_attributes

        if file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
           hidden = "Yes"
        else:
           hidden = "No"

        print(file, extension)
        print("File Size : ",file_size_kb,"KB")
        print("hidden : ",hidden)

   
except ValueError as error:
    print("Error:", error)

except FileNotFoundError as error:
    print("Error:", error)

except NotADirectoryError as error:
    print("Error:", error)

except OSError as error:
    print("Unexpected error:", error)

        



