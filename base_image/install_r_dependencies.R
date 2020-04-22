install.packages("remotes")
require("remotes")

remotes::install_github("kjhealy/covdata")

# Other Dependencies
deps <- c(
    "growthrate",
    "forecast"
)
install.packages(deps, repos='http://cran.us.r-project.org')