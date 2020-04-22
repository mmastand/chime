.fncFcstRT <- function(data, d=names(data)[1], y=names(data)[2], n=NA
                       ,h=30, minCases=20) {
   peak = .01
   data <- data[order(data[,d]),]                                                #Ensure data are ordered as expected.
   data$fcst <- 0                                                                #Indicate which values are forecasted (none, so far).
   if(is.na(n)) data$n <- minCases                                               #If number of cases not available, just set to min required cases.
   tmp <- data[,c(d,y,n)]                                                        #Get simplified copy of dataframe.
   names(tmp) <- c("d","y","n")                                                  #Rename columns for easy reference.
   tmp$x <- 1:nrow(tmp)                                                          #Get row number for prediction.
   tmp <- tmp[,c("x","d","y","n")]                                               #Reorder columns.
   tmp$use <- with(tmp, ifelse(is.na(y),0,1))                                    #Incomplete data will cause failure with ETS.
   # convert dates from string
   tmp$d <- as.Date(tmp$d)
   tmp <- rbind(tmp                                                              #Add h(orizon) days to dataframe.
                ,data.frame(x=(max(tmp$x)+1):(max(tmp$x)+h)
                            ,d=NA, n=NA, y=NA, use=1)
   )
   tmp$d <- min(as.Date(tmp$d), na.rm=TRUE)+tmp$x-1                                       #Populate dates in horizon.
   
   # Create forecasts.
   mdl <- lm(y ~ x, data=na.omit(subset(tmp, n>=minCases)))                      #Linear model.
   tmp$prd_lin <- predict(mdl, newdata=data.frame(x=tmp$x))
   
   mdl <- lm(log(y+1) ~ ns(log(x),2), data=subset(tmp, n>=minCases & y+1>0))     #Log-log model with 3-knot spline.
   tmp$prd_spln <- exp(predict(mdl, newdata=data.frame(x=tmp$x)))-1
   
   tsA <- ts(na.omit(subset(tmp, n>=minCases)$y))                                #Create time series object.
   prd <- forecast(ets(tsA, model="ZZZ", damped=TRUE), h=h)                      #Create time series forecasting model.
   tmp$prd_ets[tmp$use==1] <- c(rep(NA, nrow(subset(tmp, n<minCases))), prd$fitted, prd$mean)
   
   mdl <- loess(y ~ x, span=2, data=na.omit(subset(tmp, n>=minCases))            #Loess model.
                ,control = loess.control(surface = "direct"))
   tmp$prd_loess <- predict(mdl, newdata=data.frame(x=tmp$x))
   
   rm(mdl, prd, h, tsA)                                                          #Clean up.
   
   # Constrain predictions based upon provided peak.
   for(p in names(tmp)[grep("prd_",names(tmp))]) {                               #Go through predictions.
      tm2 <- tmp[max(which(!is.na(tmp$y))):nrow(tmp),c("x",p)]                   #Only work with projected data.
      names(tm2)[2] <- "y"                                                       #Rename column for easy access.
      if(sum(tm2$y < peak, na.rm=TRUE)==0) next                                  #Exit if there are no values over the peak limit.
      tm2$y[tm2$y<peak] <- peak                                                  #Reset values above peak to the peak.
      mdl <- lm(y ~ ns(x,3), data=tm2)                                           #Smooth values to peak.
      tm2$prd <- predict(mdl, newdata=tm2)
      # tm2$prd[min(which(tm2$prd > peak)):nrow(tm2)] <- peak                      #Remove oddities once model was found peak.
      tmp[tmp$x %in% tm2$x,p] <- tm2$prd                                         #Replace old values with new, smoothed ones <= peak.
      rm(tm2, mdl)                                                               #Clean up.
   }
   rm(p)                                                                         #Clean up.
   
   # convert date to string for pandas
   tmp$d <- as.character(tmp$d)
   
   tmp <- tmp[,c("d",names(tmp)[grep("prd_",names(tmp))])]                       #Remove unnessary columns.
   names(tmp)[1] <- d                                                            #Put original name back.
   
   tmp <- merge(data, tmp, all=TRUE)                                             #Add predictions onto original dataframe.
   tmp$fcst <- with(tmp, ifelse(is.na(fcst),1,0))                                #Indicate forecasted rows.
   
   return(tmp)
}
