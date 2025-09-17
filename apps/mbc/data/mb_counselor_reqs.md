# Unit Merit Badge Counselors V2.0

## Requirements
- Regenerate the three reports in scoutbook/legacy/test_outputs/MBC_Reports_2025-06-04_14-51/html using automatically scraped HTML data instead of manually saved HTML data.

## Design Notes
- The Merit Badge Counselor search query is https://scoutbook.scouting.org/mobile/dashboard/admin/counselorresults.asp?UnitID=82190&MeritBadgeID=&formfname=&formlname=&zip=01720&formCouncilID=181&formDistrictID=430&Proximity=25&Availability=Available
  - This query specifies:
    - UnitID=82190 -> Troop 32 Acton
    - MeritBadgeID= -> all merit badges
    - formfname= -> all first names
    - formlname= -> all last names
    - zip=01720 -> Troop 32 Acton zip code
    - formCouncilID=181 -> Heart of New England Council 230 identifier
    - formDistrictID=430 -> Quinapoxet District identifier
    - Proximity=25 -> 25 mile search radius
    - Availability=Available -> MB counselor availability
- This website responds very slowly; higher timeout settings may be needed.
- The user is to manually enter the login credentials in the browser window.
  - That is, there is no headless option.
- The search results contain a list of Merit Badge Counselors.
- The search results are paginated.
  - Multiple HTML requests are necessary to compile all search results.
- Refer to ~/Repos/beascout for guidance on scraping HTML data from Scouting America websites.
- Refer to scoutbook/legacy for documentation and code.
  - Disregard the overly complicated file structure outside of this directory.
- I will provide current troop rosters for input.
- Scraped HTML for each run is to be stored in scoutbook/data/scraped/\<YYYYMMDD\>_\<HHMMSS\>.
  - This directory will be an input into the data parsing script.

## Data Notes
- The expiration date relates to the MB counselor's Youth Protection Training (YPT).
  - If that expires, they cannot be a MB counselor
- The name is formatted as "\<first name\> [(\<alternate first name\>)] \<last name\>".
  - For example: Timothy (Tim) Werner 
- The important data for each counselor is:
  - \<div style\>
    - Name
  - \<div class="address"\>
    - Town/State/Zip
    - Phone numbers
    - Email address
  - \<div class="mbContainer"\>
    - Merit badge(s)
    - For example, the following represent the "Engineering" merit badge:
      \<div class="mb ui-corner-all ui-shadow"\>\<img src="https://d1kn0x9vzr5n76.cloudfront.net/images/icons/checkboxapproved48.png" class="mbCheckbox" title="Approved by Heart of New England Council"\>Engineering\</div\>
  - \<div class="yptDate"\>
    - YPT expiration
