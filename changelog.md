# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.2] - 2020-04-03
### Fixed
- We weren't checking to see if the user had provided `cumulative_regional_infections` before calculating `daily_regional_infections` which showed an error screen when uploading a file that didn't include `cumulative_regional_infections`.
- Now simulating exponential growth with 7, 9, and 10 day lengths of stay in the example actuals rather than polynomial growth with a 5-day LOS for each category.
### Changed
- Actuals upload widget is no longer behind a checkbox. Putting it behind the checkbox resulted in a problem where occasionally after updating other parameters the checkbox would get automatically unchecked which would hide the actuals from the charts until someone checked the actuals checkbox again. Now if you have uploaded actuals they are always shown regardless of other interactions with the sidebar.


## [1.3.1] - 2020-04-03
### Added
- Ability to upload historical data which will be displayed in the appropriate chart.
- A button to download an example csv file with historical data.
- A section at the bottom of the page which describes how to provide actuals/historical data.