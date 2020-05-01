require(EpiEstim)                                                                #For estimating R(t)
require(incidence)                                                               #Required for projections package.
require(growthrates)                                                             #Package for working with growth rates.

#
# Step 1: Probably can skip because this loads data...which you likely have.
#

rm(list=ls())                                                                    #Clean up workspace.
graphics.off()

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

# COVID-19 New York Times Data
c19 <- read.csv("https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv", stringsAsFactors=FALSE)
c19$date <- as.Date(c19$date)
sab <- state.abb; names(sab) <- state.name
c19$county <- paste(sab[c19$state], c19$county, sep=":")
c19$state <- sab[c19$state]
rm(sab)
message(paste("Last COVID-19 Date:",max(c19$date)))

# Function for getting regional data, which also allows combining counties into
# a single "region."
.fncGetRgn <- function(c19_data, pop_data, rgn, cty) {
# Need to add something to ensure no non-missing dates.

   tmp <- subset(pop_data, pop_county %in% cty)
   n <- sum(tmp$pop_est2019)
   if("NY:New York City" %in% cty) n <- sum(c(n, 8398748), na.rm=TRUE)

   tmp <- with(subset(c19_data, county %in% cty), data.frame(
             rgn     =rgn
            ,pop     =n
            ,date    =sort(unique(date))
            ,cases   =NA
            ,cumCases=tapply(cases, date, sum)
            ,fixed   =0
            ,deaths  =tapply(deaths, date, sum)
            ,row.names=NULL))
   tmp$cases <- c(tmp$cumCases[1], tmp$cumCases[2:nrow(tmp)] - tmp$cumCases[1:(nrow(tmp)-1)])

   return(tmp)
}

rgn <- list()

rgn[["AZ:Maricopa"]]      <- .fncGetRgn(c19_data=c19, pop_data=pop, rgn="AZ:Maricopa"
                                       ,cty="AZ:Maricopa")
rgn[["CA:Los Angeles"]]   <- .fncGetRgn(c19_data=c19, pop_data=pop, rgn="CA:Los Angeles"
                                       ,cty="CA:Los Angeles")
rgn[["NV:Washoe"]]        <- .fncGetRgn(c19_data=c19, pop_data=pop, rgn="NV:Washoe"
                                       ,cty="NV:Washoe")
rgn[["NY:New York City"]] <- .fncGetRgn(c19_data=c19, pop_data=pop, rgn="NY:New York City"
                                       ,cty="NY:New York City")
rgn[["UT:Salt Lake"]]     <- .fncGetRgn(c19_data=c19, pop_data=pop, rgn="UT:Salt Lake"
                                       ,cty="UT:Salt Lake")
rgn[["WA:King"]]          <- .fncGetRgn(c19_data=c19, pop_data=pop, rgn="WA:King"
                                       ,cty="WA:King")
rgn[["CA:Bay"]]           <- .fncGetRgn(c19_data=subset(c19, date>=as.Date("2020-02-23")), pop_data=pop, rgn="CA:Bay"
                                       ,cty=c("CA:Marin"
                                             ,"CA:Sonoma"
                                             ,"CA:Napa"
                                             ,"CA:Solano"
                                             ,"CA:Contra Costa"
                                             ,"CA:Alameda"
                                             ,"CA:Santa Clara"
                                             ,"CA:San Mateo"
                                             ,"CA:San Francisco"))
rgn[["WA:Multicare"]]     <- .fncGetRgn(c19_data=subset(c19, date>=as.Date("2020-02-28")), pop_data=pop, rgn="WA:Multicare"
                                       ,cty=c("WA:King"
                                             ,"WA:Snohomish"
                                             ,"WA:Pierce"
                                             ,"WA:Spokane"
                                             ,"WA:Kitsap"
                                             ,"WA:Thurston"))

#.plot_Ri <- function(estimate_R_obj) {
#    p_I <- plot(estimate_R_obj, "incid", add_imported_cases = TRUE)  # plots the incidence
#    p_SI <- plot(estimate_R_obj, "SI")  # plots the serial interval distribution
#    p_Ri <- plot(estimate_R_obj, "R")
#    return(gridExtra::grid.arrange(p_I, p_SI, p_Ri, ncol = 1))
#}

#
# Step 2: Functions for actually doing calculations.
#

# Function for estimating dynamic R(t) per EpiEstim package.
# https://doi.org/10.1093/aje/kwt133 Cori (2013)
.fncDynRt <- function(data, d=names(data)[1], y=names(data)[2]
                  ,sdn=46664, mean_si=7.5, std_si=3.4) {
   suppressMessages(require(EpiEstim))                                           #For estimating R(t)
   suppressMessages(require(incidence))                                          #Required for projections package.

   tmp <- na.omit(data[order(data[,d]),c(d,y)])                                  #Get minimum, ordered dataframe.
   names(tmp) <- c("d","n")                                                      #Rename columns for easy reference.
   inc <- with(tmp, incidence(rep(d,n)))                                         #Get incidence object.
   set.seed(sdn)                                                                 #Reset random number seed.
   res <- estimate_R(inc                                                         #Build R(t) estimate.
                    ,method="parametric_si"
                    ,config=make_config(list(mean_si=mean_si, std_si=std_si)))
   tmp <- data.frame(d    =res$dates[res$R$t_start]                              #Convert output to dataframe.
                    ,Rt   =res$R[,"Median(R)"]
                    ,RtLCL=res$R[,"Quantile.0.025(R)"]
                    ,RtUCL=res$R[,"Quantile.0.975(R)"])
   names(tmp)[1] <- d                                                            #Rename output column name for merging.
   nms <- unique(c(names(data),names(tmp)))                                      #Get names so columns can be put in order.
   data <- merge(data, tmp, all.x=TRUE)[,nms]                                    #Add R(t) data to original dataframe and restore column order.
   return(data)                                                                  #Return dataframe.
}

.fncDynRt(data=rgn[["NY:New York City"]][,c("rgn","pop","date","cases")], d="date", y="cases")

# Function for estimating dynamic doubling time per growthrates package.
# https://doi.org/10.1093/molbev/mst187 Hall (2014)
.fncDynDblTim <- function(data, d=names(data)[1], y=names(data)[2], mtry=1000) {
   require(growthrates)                                                          #Package for working with growth rates.
   dfD <- data.frame(rnm=1:nrow(data), d=data[,d], y=data[,y]                    #Initialize output dataframe.
                    ,seg=0, b0=NA, gRt=NA, dbT=NA, mthd=NA)
   dfD <- dfD[order(dfD$d),]                                                     #Ensure dataframe is ordered as expected.
   
   if(any(dfD$y[2:nrow(dfD)] < dfD$y[1:(nrow(dfD)-1)]))                          #Ensure cumulative cases are provided.
      stop("Dynamic doubling time calcluations require cumulative cases")

   a <- 1                                                                        #Initialize number of attempts.

   repeat {                                                                      #While there are rows to estimate...
      if(sum(is.na(dfD$gRt)) < 2) break                                          #Stop if there aren't enough records without rates.

      tmp <- subset(dfD, is.na(gRt))                                             #Get subset of records where growth rate has not been estimated.

      # Find largest remaining candidate contiguous segment to feed into growth
      # rate routine.
      csg <- 0; tmp$csg <- 0                                                     #Initialize candidate contiguous time segments.
      for(i in 2:nrow(tmp)) {                                                    #Find contiguous segments (series will have been split by already estimated growth rates).
         if((tmp$rnm[i]-1) != tmp$rnm[i-1]) csg <- csg-1                         #If rows not contiguous, start new candidate segment.
         tmp$csg[i] <- csg
      }
      rm(csg,i)                                                                  #Clean up.

      t2 <- table(tmp$csg)                                                       #Find candidate segment sizes.

      if(max(t2) < 2) break                                                      #Stop if there no contiguous segments with at least 2 points.

      tmp <- tmp[tmp$csg==as.numeric(names(which(t2==max(t2))))[1],]             #Limit dataframe to selected largest remaining segment.

      # Find growth rate in selected segment.  The auto-select routine will
      # find the highest growth rate sub-segment within the overall segment it
      # it receives.
      fit <- NULL; m <- "auto"                                                   #Ensure fit starts as NULL object and default method of "auto."
      try(fit <- with(tmp, fit_easylinear(d, y))@fit, TRUE)                      #Calculate growth rate for linear growth portion.
      if(is.null(fit)) {                                                         #If auto-calc fails, try to calculate growth rate with simple linear model.
         m <- "lm"                                                               #Specify type of model used.
         try(fit <- with(tmp, lm(log(y) ~ d)), TRUE)                             #Fit linear model.
         names(fit$model)[2] <- "x"                                              #Change name of variable to be consistent with auto model.
      }

      if(!is.null(fit)) {                                                        #If fit works...
         dfD$seg[dfD$d %in% fit$model$x]  <- max(dfD$seg)+1                      #Populate segment.
         dfD$b0[dfD$d %in% fit$model$x]   <- fit$coef[1]                         #Populate intercept.
         dfD$gRt[dfD$d %in% fit$model$x]  <- fit$coef[2]                         #Populate growth rate.
         dfD$mthd[dfD$d %in% fit$model$x] <- m                                   #Specify method.
      }

      a <- a+1                                                                   #Increment number of attempts and break out if exceeded limit.
      if(a > mtry) { message(paste("STOPPED after",a,"attempts")); break }
   }
   dfD$dbT <- log(2)/dfD$gRt                                                     #Calculate doubling time.

   for(i in which(is.na(dfD$dbT))) {
      dfD$dbT[i] <- mean(c(tail(subset(dfD[1:(i-1),], !is.na(dbT)),1)$dbT
                          ,head(subset(dfD[(i+1):nrow(dfD),], !is.na(dbT)),1)$dbT
                          ), na.rm=TRUE)
      dfD$mthd[i] <- "impute"
   }

   dfD <- dfD[,-c(1,3)]                                                          #Remove row number and cumulative cases columns.
   names(dfD)[1] <- d                                                            #Rename columns back to originals.
   nms <- unique(c(names(data),names(dfD)))
   data <- merge(data, dfD, all.x=TRUE)[,nms]                                    #Add columns to original dataframe.

   return(data)                                                                  #Return dataframe.
}

.fncDynDblTim(data=rgn[["NY:New York City"]][,c("rgn","pop","date","cumCases")], d="date", y="cumCases")

# Function for producing forecasts for provided values.
.fncFcst <- function(data, d=names(data)[1], y=names(data)[2], n=NA
                    ,mthds=c("lin","spln","ets","loess")
                    ,pfx=y
                    ,h=30, minCases=20, peak=max(data[,y], na.rm=TRUE)*2, trough=NA) {
   suppressMessages(require(splines))                                            #Load package for splines.
   suppressMessages(require(forecast))                                           #Forecast package.

   sng <- names(data)[which(sapply(data, function(x) length(unique(x)))==1)]     #Single value columns.

   tmp <- data[order(data[,d]),setdiff(c(d,y,n),NA)]                             #Ensure data are ordered as expected.
   if(is.na(n)) tmp$n <- minCases                                                #If number of cases not available, just set to min required cases.
   names(tmp) <- c("d","y","n")                                                  #Rename columns for easy reference.
   tmp$x <- 1:nrow(tmp)                                                          #Get row number for prediction.
   tmp <- tmp[,c("x","d","y","n")]                                               #Reorder columns.
   tmp$prj <- ifelse(tmp$d >= min(subset(tmp, !is.na(y) & d<max(tmp[!is.na(tmp$y),]$d))$d), 1, 0)

   if(inherits(h, "Date")) { h <- as.integer(h - max(tmp$d))                     #Take date-based horizon and convert to integer days forward.
   } else if(h>0 & length(grep("prd_",names(data)))>0) {                         #Warn if days forward provided and forecasts arleady in dataframe.
      h <- as.integer((max(subset(tmp, !is.na(y))$d)+h) - max(tmp$d))            #Recalculate horizon.
      if(h>0) message("Warning: Forecast already present and non-date based horizon provided.")
   }

   if(h>0) {                                                                     #If horizon is not already covered.
      tmp <- rbind(tmp                                                           #Add h(orizon) days to dataframe.
                  ,data.frame(x=(max(tmp$x)+1):(max(tmp$x)+h)
                             ,d=NA, n=NA, y=NA, prj=1)
                  )
      tmp$d <- min(tmp$d, na.rm=TRUE)+tmp$x-1                                    #Populate dates in horizon.
   }
   tmp$use <- with(tmp, ifelse(!is.na(y) & n>=minCases, 1, 0))                   #Figure out what can be used for building forecast.
   h <- sum(tmp$d > max(subset(tmp, !is.na(y))$d))                               #Reset horizon.

   # Create forecasts.
   if("lin" %in% mthds) {                                                        #Produce linear model forecast if requested.
      mdl <- lm(y ~ x, data=subset(tmp, use==1))
      tmp$prd_lin <- predict(mdl, newdata=data.frame(x=tmp$x))
      rm(mdl)
   }

   if("spln" %in% mthds) {                                                       #Produce log-log model with 3-knot spline if requested.
      mdl <- lm(log(y+1) ~ ns(log(x),2), data=subset(tmp, use==1 & y+1>0))
      tmp$prd_spln <- exp(predict(mdl, newdata=data.frame(x=tmp$x)))-1
      rm(mdl)
   }

   if("ets" %in% mthds) {                                                        #Produce time series forecast if requested.
      tsA <- ts(na.omit(subset(tmp, use==1 & prj==1)$y))
      prd <- forecast(ets(tsA, model="ZZZ", damped=TRUE), h=h)
      tmp$prd_ets[tmp$d>=min(subset(tmp,use==1)$d)] <- c(prd$fitted, prd$mean)
      tmp$prd_ets[tmp$d<min(subset(tmp,use==1)$d)] <- c(prd$fitted[1])
      rm(tsA,prd)
   }

   if("loess" %in% mthds) {                                                      #Produce loess model forecast if requested.
      mdl <- loess(y ~ x, span=2, data=subset(tmp, use==1)
                  ,control = loess.control(surface = "direct"))
      tmp$prd_loess <- predict(mdl, newdata=data.frame(x=tmp$x))
      rm(mdl)
   }

   rm(h)                                                                         #Clean up.

   # Constrain predictions based upon provided peak.
   for(p in names(tmp)[grep("prd_",names(tmp))]) {                               #Go through predictions.
      tm2 <- tmp[max(which(!is.na(tmp$y))):nrow(tmp),c("x",p)]                   #Only work with projected data.
      names(tm2)[2] <- "y"                                                       #Rename column for easy access.
      if(sum(tm2$y > peak, na.rm=TRUE)==0) next                                  #Exit if there are no values over the peak limit.
      tm2$y[tm2$y>peak] <- peak                                                  #Reset values above peak to the peak.
      mdl <- lm(y ~ ns(x,3), data=tm2)                                           #Smooth values to peak.
      tm2$prd <- predict(mdl, newdata=tm2)
      tm2$prd[min(which(tm2$prd > peak)):nrow(tm2)] <- peak                      #Remove oddities once model was found peak.
      tmp[tmp$x %in% tm2$x,p] <- tm2$prd                                         #Replace old values with new, smoothed ones <= peak.
      rm(tm2, mdl)                                                               #Clean up.
   }
   rm(p)                                                                         #Clean up.

   # Constrain predictions based upon provided trough.
   if(!is.na(trough)[1]) {                                                       #If trough provided...
      for(p in names(tmp)[grep("prd_",names(tmp))]) {                            #Go through predictions.
         tm2 <- tmp[max(which(!is.na(tmp$y))):nrow(tmp),c("x",p)]                #Only work with projected data.
         names(tm2)[2] <- "y"                                                    #Rename column for easy access.
         if(sum(tm2$y < trough, na.rm=TRUE)==0) next                             #Exit if there are no values below the trough limit.
         tm2$y[tm2$y>trough] <- trough                                           #Reset values above trough to the trough.
         mdl <- lm(y ~ ns(x,3), data=tm2)                                        #Smooth values to trough.
         tm2$prd <- predict(mdl, newdata=tm2)
         tm2$prd[min(which(tm2$prd < trough)):nrow(tm2)] <- trough               #Remove oddities once model was found trough.
         tmp[tmp$x %in% tm2$x,p] <- tm2$prd                                      #Replace old values with new, smoothed ones >= trough.
         rm(tm2, mdl)                                                            #Clean up.
      }
      rm(p)                                                                      #Clean up.
   }

   tmp <- tmp[,c("d",names(tmp)[grep("prd_",names(tmp))])]                       #Remove unnessary columns.
   names(tmp)[1] <- d                                                            #Put original name back.

   names(tmp) <- gsub("prd_",paste0(pfx,"_prd_"),names(tmp))                     #Add prefix to prediction column names.
   nms <- unique(c(names(data),names(tmp)))                                      #Get order of columns.
   data <- merge(data, tmp, all=TRUE)[,nms]                                      #Add predictions onto original dataframe.

   for(n in sng) data[,n] <- data[1,n]                                           #Replicate constants across entire dataframe.

   return(data)
}

# Function for generating SIR output.
# data      = dataframe
# d         = date/day cases were found
# cases     = incident cases
# pop       = regional population where cases appeared
# infect_dys= days someone stays infected
# grw       = column with growth--either Rt (R(t)) or dbT (doubling time)
# fcst      = colomn with forecasted growth rates
# useAct    = should actual cases be used when available
# # Replicate Penn Med with parameters:
# # Pop=1MM; Hospital Mkt Shr=100%; Current Hosp=1; First Case=2020/03/01
# # Today=2020/03/01; Infectious days=10; Social Distancing=0%
# # Hospitalization=100%; ICU=0%; Ventilated=0%
# tst <- data.frame(rgn="Fabricated Test"
#                  ,date=seq(from=as.Date("2020-03-01"), by=1, length.out=100)
#                  ,cases=NA, pop=1000000)
# tst$dbT <- 2.862244897959184
# tst$Rt <- 3.740096 #Calculated from MS Excel file by plugging doubling time and infectious days.
# subset(.fncSIR(data=tst, pop=tst$pop[1], infect_dys=10, grw="Rt" ), date %in% as.Date(c("2020-03-20","2020-06-08")))
# subset(.fncSIR(data=tst, pop=tst$pop[1], infect_dys=10, grw="dbT"), date %in% as.Date(c("2020-03-20","2020-06-08")))
# tst <- .fncSIR(data=tst, pop=tst$pop[1], infect_dys=10, grw="Rt" )
# .fncPlotSIR(tst)
# rm(tst)

.fncSIR <- function(data, d="date", cases="cases", pop, infect_dys
                   ,grw="Rt", fcst=NA, useAct=FALSE) {

   # (Try to) find forecast column.
   if(!is.na(fcst)) {                                                            #Forecast column provided...
      tf <- fcst                                                                 #Store forecast value.
      if(!(fcst %in% names(data))) fcst <- paste0(grw,"_prd_",tf)                #If provided value not found, build standard formant construction.
      if(!(fcst %in% names(data))) stop(paste("Forecast column",tf,"not found")) #If that can't be found, stop with message.
   }

   # Prep dataframe.
   tmp <- data[order(data[,d]),na.omit(c(d,cases,grw,fcst))]                     #Get minimum dataframe.
   names(tmp) <- na.omit(c("d","cases","grw",ifelse(!is.na(fcst),"fcst",NA)))    #Rename columns for easy reference.
   if(sum(!is.na(tmp$cases))==0) tmp$cases[1] <- 1                               #Initialize cases, if none provided.
   tmp$cumCases <- cumsum(tmp$cases)                                             #Get cumulative sum of cases.

   # Set constants and initial values.
   g <- 1 / infect_dys                                                           #Gamma.
   tmp$b <- NA                                                                   #Initialize beta.
   tmp$s[1] <- pop - tmp$cumCases[1]                                             #Initialize Susceptible, Infected, and Recovered.
   tmp$i[1] <- tmp$cases[1]
   tmp$r[1] <- 0
   tmp$t[1] <- 1
   tmp$n[1] <- tmp$i[1]                                                          #Derived new cases (will be lower than current total Infected).
   tmp$rst <- 0                                                                  #Flag for whether row is reset to actuals.

   # Calculate beta.
   x <- tmp$grw                                                                  #Array for doubling time.
   if(!is.na(fcst)) x <- ifelse(!is.na(tmp$grw), tmp$grw, tmp$fcst)              #Use forecast when no actual.
   if(tolower(grw)=="dbt") { tmp$b <- ((2^(1/x))-1 + g) / tmp$s[1]               #Calculate beta from doubling time.
   } else                  { tmp$b <- x * g / tmp$s[1]              }            #Calculate beta from R(t).
   rm(x)                                                                         #Clean up.

   m <- c("Linear","Log-Spline","Loess","ETS")                                   #Label for growth method and forecasting approach.
   names(m) <- c("lin","spln","loess","ets")
   m <- m[tolower(gsub(".*prd_","",fcst))]
   if(is.na(m)) m <- fcst
   tmp$mSIR <- paste(ifelse(tolower(grw)=="dbt","Doubling Time","Reproduction Number")
                    ,m
                    ,ifelse(useAct,"Actual Reset","Theoretic"), sep=", ")
   rm(m)                                                                         #Clean up.

   # Calculate SIR.
   for(i in 2:nrow(tmp)) {                                                       #Loop through rows...
      p <- i-1                                                                   #Store prior index for easy reading.
      tmp$s[i] <- -tmp$b[i] * tmp$s[p] * tmp$i[p] + tmp$s[p]                     #Calculate Susceptible, Infected, and Recovered.
      tmp$i[i] <- ((tmp$b[i]*tmp$s[p]*tmp$i[p]) - (g*tmp$i[p])) + tmp$i[p]
      tmp$r[i] <- (g*tmp$i[p]) + tmp$r[p]
      if(useAct & !is.na(tmp$cases[i])) {                                        #If user requests to use actual and data available...
         tmp$s[i] <- tmp$s[i-1] - (tmp$cumCases[i-1])                            #Reset Susceptible, Infected, and Recovered.
         tmp$i[i] <- sum(tmp$cases[i:(i-min(c(i,infect_dys-1)))])
         tmp$r[i] <- ifelse(i>infect_dys, tmp$cumCases[i-infect_dys], 0)
         tmp$rst[i] <- 1
      }
      tmp$t[i] <- tmp$i[i] + tmp$r[i]     #Why are "recovered" counted in here? (Per Penn Med admission formula)
      tmp$n[i] <- tmp$t[i] - tmp$t[i-1]
   }
   rm(i,p)                                                                       #Clean up.

   # Remerge calculations with original data.
   names(tmp)[1] <- d                                                            #Rename column for merging.
   tmp <- tmp[,setdiff(names(tmp),setdiff(intersect(names(data),names(tmp)),d))] #Remove non-merging duplicate columns.
   nms <- unique(c(names(data),setdiff(names(tmp),c("t","grw","fcst"))))         #Get order of columns.
   data <- merge(data, tmp, all=TRUE)[,nms]                                      #Add predictions onto original dataframe.

   return(data)
}

#
# Step 3: Probably can skip because this because for plotting.
#

.fncPlotGrw <- function(data, d="date", grw="Rt", cases="cases"
                       ,ylm=NA, actOnly=FALSE) {
   yvl <- names(data)[grep(paste0(grw,"."),names(data))]                         #Key y-value columns.
   tmp <- data[,c(d,cases,yvl)]                                                  #Get key columns.
   if(actOnly) tmp <- tmp[!is.na(tmp[,cases]),]                                  #Restrict to actuals if requested.
   names(tmp)[1] <- "d"                                                          #Rename column for easier reference.

   ylm <- range(tmp[,yvl], na.rm=TRUE)

#   plot(x=

   print(head(tmp))
}

#.fncPlotGrw(dat)

# Function for plotting SIR and also new cases (different from Infected).
.fncPlotSIR <- function(data, d="date", cases=NA, ylm=NA, showSIR=TRUE) {
   par(mar=c(3,4,3,1), cex.axis=0.8, las=1)                                      #Set plotting parameters.
   tmp <- data[,c(d,"s","i","r","n","rst")]                                      #Restrict to minimum dataframe.
   names(tmp)[which(names(tmp)==d)] <- "d"                                       #Rename column for easier reference.
   tmp$a <- NA; if(!is.na(cases)) tmp$a <- data[,cases]                          #Populate actuals, if they exist.
   if(is.na(ylm[1])) ylm <- range(tmp[,c("s","i","r","a","n")],na.rm=TRUE)       #Set automated y-axis limits.
   with(tmp, plot(x=range(tmp$d), y=ylm, type="n", main="", xlab="", ylab=""
                 ,axes=FALSE))
   rgn <- ifelse(!is.null(data$rgn[1]),as.character(data$rgn[1]),"")             #Get region name, if there is one.
   mtext(paste0(rgn," SIR Model"), line=1.5, font=2)                             #Place title.
   mtext(data$mSIR[1], line=0.5, cex=0.8)
   ax <- axTicks(1); ay <- axTicks(2); grid(); box()                             #Place grid, box, and axes.
   axis(1, at=ax, labels=as.Date(ax, origin="1970-01-01"))
   ayl <-  ifelse(ay+1>10^6, paste0(sprintf("%2.1f",ay/10^6),"MM")
          ,ifelse(ay+1>10^3, paste0(sprintf("%2.1f",ay/10^3),"K"), ay))
   axis(2, at=ay, labels=ayl)
   if(sum(!is.na(tmp$a))>0)                                                      #Show actual period, if there was one.
      with(subset(tmp, !is.na(a)), lines(x=range(d), y=c(0,0), col="green", lwd=8))
   if(sum(tmp$rst, na.rm=TRUE)>0)                                                #Show reset period, if there was one.
      with(subset(tmp, rst==1), lines(x=range(d), y=c(0,0), col="yellow", lwd=4))
   lgs <- cls <- NA                                                              #Initialize SIR legend and color entries.
   if(showSIR) {                                                                 #If SIR curves requested...
      with(tmp, lines(x=d, y=s, lwd=2, col="red"))
      with(tmp, lines(x=d, y=r, lwd=2, col="orange"))
      with(tmp, lines(x=d, y=i, lwd=2, col="blue"))
      lgs <- c("Susceptible","Infected","Recovered")
      cls <- c("red","blue","orange")
   }
   with(tmp, lines(x=d, y=n, lwd=2, col=ifelse(sum(!is.na(tmp$a))==0,"black","gray")))
   with(tmp, lines(x=d, y=a, lwd=2, col="black"))
   legend("topright", bg="white", ncol=1, cex=0.7, pch=22, pt.cex=1.5, col=NA    #Legend for interpretation.
         ,legend=na.omit(c(lgs,"Actual","Reset","New Cases","Forecast"))
         ,pt.bg=na.omit(c(cls,"green","yellow","black","gray")))
}

#
# Step 4: This is the function that will take your input data and produce your
#         output data.
#

# Function for single call from input case data through (forecasted) SIR calculation.
# Input: Dataframe with...
# - rgn        = Region name
# - pop        = Population size (typically from government census)
# - d          = Day/date for spread
# - cases      = New/incident cases (typically from New York Times or Johns Hopkins)
# - cumCases   = Cumulative cases through day/date
#
# Input: Parameters...
# - hdt        = Horizon date (what data to forecast through)
# - fcst_mthds = Forecast methods to attempt (linear, log-spline, time series, and loess)
# - fcst_trough= Manual lower limit for forecast (can help R(t) forecast)
# - fcst_peak  = Manual higher limit for forecast (can help doubling time forecast)
# - infect_dys = Number of days someone stays infected
# - grw        = Growth method to use for SIR model (Rt or dbT)
# - fcst       = Foreacst method to use for SIR model (from above methods)
# - useAct     = Whether to override SIR model with actual when available
#
# Output: Dataframe with all columns specified above and...
# ... Calculations for dynamic reproduction number R(t) -- .fncDynRt
# - Rt         = R(t)
# - RtLCL      = R(t) lower 95% confidence level
# - RtUCL      = R(t) upper 95% confidence level
# ... Calculations for dynamic doubling time -- .fncDynDblTim
# - seg        = Segment for calculating growth rate
# - b0         = Intercept term for growth model
# - gRt        = Estimated growth rate for model
# - dbT        = Estimated doubling time
# - mthd       = Method for calulating doubling time (auto, linear model, imputed)
# ... Forecasts for R(t) and doubling time -- .fncFcst
# - Rt_prd_X   = R(t) forecast where 'X' is each requested forecasted method
# - dbT_prd_X  = Doubling time forecast where 'X' is each requested forecasted method
# ... Components for SIR model
# - b          = beta (dynamic and derived from R(t) or doubling time)
# - s          = Susceptible population remaining
# - i          = Currently infected (depends upon infect_dys)
# - r          = Recovered so far
# - n          = New infections
# - rst        = Reset SIR values based upon actuals (requires actual and useAct=TRUE)
# - mSIR       = Text description of methods used.
.fncCaseEst <- function(data, rgn="rgn", pop="pop", d="date", cases="cases", cumCases="cumCases"
                       ,hdt=max(data[,d], na.rm=TRUE)+30
                       ,fcst_mthds=c("lin","spln","ets","loess"), fcst_trough=NA, fcst_peak=NA
                       ,infect_dys=10, grw="dbT", fcst="ets", useAct=TRUE) {
   dat <- data[,c(rgn,pop,d,cases,cumCases)]
   dat <- .fncDynRt(data=dat, d=d, y=cases)
   dat <- .fncDynDblTim(data=dat, d=d, y=cumCases)
   dat <- .fncFcst(dat, d=d, y="Rt" , n=cumCases, mthds=fcst_mthds, h=hdt, trough=fcst_trough)
   dat <- .fncFcst(dat, d=d, y="dbT", n=cumCases, mthds=fcst_mthds, h=hdt, peak=fcst_peak)
   dat <- .fncSIR(data=dat, pop=dat[1,pop], infect_dys=infect_dys, grw=grw, fcst=fcst, useAct=useAct)

   return(dat)
}

#
# Step 5: Examples of how to call functions.
#

tst <- .fncCaseEst(rgn[["CA:Los Angeles"]][,c("rgn","pop","date","cases","cumCases")]
                  ,fcst_mthds=c("spln","ets","loess"), fcst_trough=0, hdt=as.Date("2020-08-31")
                  ,infect_dys=10, grw="dbT", fcst="spln", useAct=TRUE)
graphics.off()
x11(h=4,w=4)
.fncPlotSIR(tst, cases="cases", ylm=c(0, 2*max(tst$n,na.rm=TRUE)), showSIR=FALSE)
rm(tst)

#dat <- rgn[["AZ:Maricopa"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["CA:Bay"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["CA:Los Angeles"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["NV:Washoe"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["NY:New York City"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["UT:Salt Lake"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["WA:King"]][,c("rgn","pop","date","cases","cumCases")]
#dat <- rgn[["WA:Multicare"]][,c("rgn","pop","date","cases","cumCases")]
hdt <- as.Date("2020-08-31")
dat <- .fncDynRt(data=dat, d="date", y="cases")
dat <- .fncDynDblTim(data=dat, d="date", y="cumCases")
dat <- .fncFcst(dat, d="date", y="Rt" , n="cumCases", mthds=c("spln","ets","loess"), h=hdt, trough=0)
dat <- .fncFcst(dat, d="date", y="dbT", n="cumCases", mthds=c("spln","ets","loess"), h=hdt)
dat <- .fncSIR(data=dat, pop=dat$pop[1], infect_dys=10, grw="dbT", fcst="ets", useAct=TRUE)
graphics.off()
x11(h=4,w=4)
.fncPlotSIR(dat, cases="cases", ylm=c(0, 2*max(dat$n,na.rm=TRUE)))

ddr <- "C:/Users/jason.jones/Health Catalyst, Inc/Data Science - Documents/Products/COVID19/DynamicDoubling/SampleData/"
hdt <- as.Date("2020-08-31")

for(n in names(rgn)) {
   print(gsub(":","_",n))
   dat <- rgn[[n]][,c("rgn","pop","date","cases","cumCases")]
   write.table(dat, file=paste0(ddr,gsub(":","_",n),"_In.txt"), quote=FALSE, sep="\t", na="", row.names=FALSE)
   dat <- .fncDynRt(data=rgn[[n]], d="date", y="cases")
   dat <- .fncDynDblTim(data=dat, d="date", y="cumCases")
   dat <- .fncFcst(dat, d="date", y="Rt" , n="cumCases", mthds=c("spln","ets","loess"), h=hdt, trough=0)
   dat <- .fncFcst(dat, d="date", y="dbT", n="cumCases", mthds=c("spln","ets","loess"), h=hdt)
   dat <- .fncSIR(data=dat, pop=dat$pop[1], infect_dys=10, grw="dbT", fcst="ets", useAct=TRUE)
   write.table(dat, file=paste0(ddr,gsub(":","_",n),"_Out.txt"), quote=FALSE, sep="\t", na="", row.names=FALSE)
   rm(dat)
}
rm(n,hdt,ddr)