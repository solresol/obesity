Obesity investigation
=====================

Inspired by the observation that obesity seems to decline in prevalence with increasing altitude
in the USA, is the same true in Australia?

Data
----

I found  `aust_health_tracker_data_lga.xlsx` at https://atlasesaustralia.com.au/ahpc/

This has obesity-related information.

Altitude information is fetched from wikidata.

Economic indicators are fetched from the ABS.


Naive approach
--------------

The naive approach -- just correlate altitude with obesity percentages -- suggests not. 

How to reproduce it:

- Run `altitude.sparql` on `query.wikidata.org`  This should produce `altitudes.csv`

- Run `Join helath stats with altitude.ipynb` . About half-way down, it creates `chart-ready-data.csv`

- Run `analysis-charts.twb` in Tableau. 

I was exploring a little, not being overly scientific about this, so there are some weird
charts in Tableau as well.


More sophisticated approach
---------------------------

The second half of `Join health stats with altitude.ipynb` fetches economic indicators.

There's a small bug in it where if it fetches a file-not-found page from the ABS it just carries
on anyway without saving valid data. I deleted the invalid files by hand.

The method is:

- Remove numeric counts from the source data; rely on percentages instead.

- Do robust scaling to put all source information on a standard scale.

- Create a lasso model for each of the targets
  (obesity/overweight/gender/age range); use cross-validation to find
  the appropriate alpha value to maximise the accuracy of the model. 
  
- Read off the coefficients from the lasso model in decreasing absolute value.

This kind of model should cope with collinearity -- if there are
two highly collinear data columns, one will be given a zero coefficient, and the one
with greater relevant variability should end up with an appropriate coefficient.
