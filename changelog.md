# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2020-04-08
### Added
- Sidebar parameters to represent PPE supplies needed per patient per day.
- Charts show PPE needed per day, based on census.
- Descriptions and file IO now support parameters and required PPE.
### Modified
- Minimum days to project is now 7.

## [1.3.7] - 2020-04-07
### Fixed
- Setting the number of projected days no longer has any effect on the date of the first admitted case or beginning of the date series.
- Total census is now a sum of ICU and non-ICU, rather than cumulative sum of total hospital admissions. See the effects of this change by setting
ICU LOS to 50.

## [1.3.5]
### Fixed
- The mismatched census warning function wasn't checking if the actuals dataframe contained a total census column so we got a missing column exception if the user uploaded actuals without a census column.

## [1.3.4] - 2020-04-06
### Added 
- The ability to upload historical data which is now displayed alongside the projected data in the charts.
- A warning that appears if the manually-entered census value from the sidebar does not match the census value provided in the actuals.
- A section at the bottom of the page with release notes and changes by version.
### Changed
- The "Hospital Capacity" section header to "COVID-19 Hospital Capacity".
### Fixed
- Hopefully fixed the tooltip bug where the tooltip was showing the date value as one day behind the actual uploaded/calculated date values.

## [1.3.3] - 2020-04-03
### Fixed
- Penn's model had a bug where if you provided a first hospitalized date instead of a doubling time the model sometimes picked a point on the backside of the maximum as today.

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