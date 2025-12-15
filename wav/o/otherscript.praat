# This script processes all TextGrid files in the Objects window
# and prints vocal fry durations to the Info window

# Clear Info window and write header
clearinfo
writeInfoLine: "Filename", tab$, "Sounding_duration", tab$

# Get all TextGrid objects and store their IDs
n = numberOfSelected ("TextGrid")
for i to n
    textgrid'i' = selected ("TextGrid", i)
endfor

# Now loop through and process each one
for i to n
    selectObject: textgrid'i'
    name$ = selected$ ("TextGrid")
    
    # Get total duration of 'c' intervals (tier 1, adjust if different)
    sounding_duration = Get total duration of intervals where: 1, "is equal to", "sounding"
    
    # Write to Info window
    appendInfoLine: name$, tab$, sounding_duration
endfor

appendInfoLine: ""
appendInfoLine: "Done! Processed ", n, " TextGrids."