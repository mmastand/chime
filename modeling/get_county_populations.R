# https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv

rm(list=ls())

# Read in census data.
pop <- read.csv("https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv")
names(pop) <- tolower(names(pop))                                                #Convert names to lower case.
pop <- pop[,c("state","county","stname","ctyname","popestimate2019")]            #Retain only desired columns.
pop$fips <- with(pop, as.integer(paste0(state,sprintf("%03.0f",county))))        #Generate FIPS code from components.
sab <- merge(data.frame(stname=sort(unique(pop$stname)), stringsAsFactors=FALSE)
            ,data.frame(stname=state.name, state.abb, stringsAsFactors=FALSE), all=TRUE)
sab[sab$stname=="District of Columbia",]$state.abb <- "DC"
pop <- merge(pop, sab, all.x=TRUE)
pop <- subset(pop, county!=0)                                                    #Remove non-counties (e.g., states).
pop$ctyname <- with(pop, gsub(" County",""                                       #Remove add-ons not present in NYT data from county names.
                        ,gsub(" Municipality",""
                        ,gsub(" Parish", "", ctyname))))
pop$ctyname <- with(pop, paste(state.abb, ctyname, sep=":"))                     #Add state prefix to county.
pop <- pop[,c("fips","ctyname","popestimate2019")]                               #Restrict and order columns as desired.
names(pop)[2:3] <- c("pop_county","pop_est2019")

# Read in COVID-19 data.
c19 <- read.csv("https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv", stringsAsFactors=FALSE)
c19$date <- as.Date(c19$date)
sab <- state.abb; names(sab) <- state.name
c19$state <- sab[c19$state]
c19$county <- with(c19, paste(state, county, sep=":"))
rm(sab)
message(paste("Last COVID-19 Date:",max(c19$date)))

# Merge and check data based upon FIPS.
chk <- with(c19, data.frame(
          c19_county =sort(unique(county))
         ,fips       =tapply(fips, county, min)
         ,cumCases   =tapply(cases, county, max)
         ,row.names=NULL, stringsAsFactors=FALSE))

chk <- merge(chk, pop, all.x=TRUE)                                               #Merge data on basis of FIPS code.
subset(chk, is.na(pop_county))                                                   #Rows without pop data (note, NYC is one).
subset(chk, c19_county != pop_county)                                            #Rows with mismatched counties.