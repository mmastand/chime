# require(EpiEstim)                                                                #For estimating R(t)
# require(incidence)                                                               #Required for projections package.
# require(growthrates)                                                             #Package for working with growth rates.

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

   print(paste0("h: ", h, " Class h: ", class(h)))

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
                       ,fcst_mthds=c("lin","spln","ets","loess"), fcst_trough=NA, fcst_peak=NA
                       ,infect_dys=10, grw="dbT", fcst="ets", useAct=TRUE) {
   data$date <- as.Date(data[,d])
   hdt <- max(data[,d], na.rm=TRUE)+30
   dat <- data[,c(rgn,pop,d,cases,cumCases)]
   dat <- .fncDynRt(data=dat, d=d, y=cases)
   dat <- .fncDynDblTim(data=dat, d=d, y=cumCases)
   # dat <- .fncFcst(dat, d=d, y="Rt" , n=cumCases, mthds=fcst_mthds, h=hdt, trough=fcst_trough)
   print(paste("hdt", hdt))
   dat <- .fncFcst(dat, d=d, y="dbT", n=cumCases, mthds=fcst_mthds, h=hdt, peak=fcst_peak)
   dat <- .fncSIR(data=dat, pop=dat[1,pop], infect_dys=infect_dys, grw=grw, fcst=fcst, useAct=useAct)

   return(dat)
}