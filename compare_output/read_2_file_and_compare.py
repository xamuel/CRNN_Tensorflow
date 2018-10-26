# Ask the user to enter the names of files to compare
fname1 = input("Enter the first filename: ")
fname2 = input("Enter the second filename: ")

# Open file for reading in text mode (default mode)
f1 = open(fname1)
f2 = open(fname2)

# Print confirmation
print("-----------------------------------")
print("Comparing files ", " > " + fname1, " < " +fname2, sep='\n')
print("-----------------------------------")

# Read the first line from the files
f1_line = f1.readline()
f2_line = f2.readline()

# Initialize counter for line number
line_no = 1
error_count = 0
match_count = 0
# Loop if either file1 or file2 has not reached EOF
while f1_line != '' or f2_line != '':

    # Strip the leading whitespaces
    f1_line = f1_line.rstrip()
    f2_line = f2_line.rstrip()

    # Compare the lines from both file
    if f1_line != f2_line:
        error_count += 1
        with open('diff.txt', 'a') as the_file: 
          the_file.write(f1_line + " = " + f2_line + "\n")
    else:
        match_count +=1

    #Read the next line from the file
    f1_line = f1.readline()
    f2_line = f2.readline()


    #Increment line counter
    line_no += 1
print("error_count",error_count)
print("match_count",match_count)  
# Close the files
f1.close()
f2.close()
