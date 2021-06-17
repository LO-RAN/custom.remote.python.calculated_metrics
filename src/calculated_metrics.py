"""

The purpose of this plugin is to gather 1 to 10 metrics from Dynatrace, apply an arithmetic expression on the retrieved values and push back the result as a new ingest.
Being an ActiveGate plugin, it triggers every minute.

Note: It uses API v2 only. It does not create any device nor device related data.


Inputs will be : 
- ordered list of 1 to 10 existing metric selectors 
    Note: each selector will be assigned to a letter from A to J (first selector will be A, second will be B, ...)
- formula (mathematical expression) to compute on the values retrieved for each provided selector, using placeholders in the form of letters from A to J.
    Example : "(A/B)*100"   
    Note: before evaluating the expression, A will be replace by the value found for the first provided selector, B for the second, ...
- name of the metrics to populate with the evaluation result.



Example API calls and responses, used as source material to build this plugin
=============================================================================

###  get metrics values for a given metrics, with a resolution of 1 minute, for the last 2 minutes (the last 1 inute would often provide no data)

 curl -X GET "https://<CHANGE_ME>.live.dynatrace.com/api/v2/metrics/query?metricSelector=<CHANGE_ME>&resolution=1m&from=-2m" 
      -H "accept: application/json; charset=utf-8" 
      -H "Authorization: Api-Token <CHANGE_ME>"

OK=200 

{
  "totalCount": 1,
  "nextPageKey": null,
  "result": [
    {
      "metricId": "...",
      "data": [
        {
          "dimensions": [
            "...",
            "All requests"
          ],
          "dimensionMap": {
            "dt.entity.service": "...",
            "Dimension": "All requests"
          },
          "timestamps": [
            1616766420000,
            1616766480000,
            1616766540000
          ],
          "values": [
            45,
            null,
            null
          ]
        }
      ]
    }
  ]
}




### post new data, providing metrics name, value and (optionally) timestamp

curl -X POST "https://<CHANGE_ME>.live.dynatrace.com/api/v2/metrics/ingest" 
     -H "accept: */*" 
     -H "Authorization: Api-Token <CHANGE_ME>" 
     -H "Content-Type: text/plain; charset=utf-8" 
     -d "ratio.sample 42 1616766540000"


OK = 202

"""


from ruxit.api.base_plugin import RemoteBasePlugin
import json
import logging
import requests
from functools import reduce
from mathrepl import evaluate

logger = logging.getLogger(__name__)

class Generator(RemoteBasePlugin):

    def initialize(self, **kwargs):

        config = kwargs['config']
        debugLogging = config["debug"]

        # get input parameters

        if debugLogging == "DEBUG":
            self.logging_level = logging.DEBUG
        elif debugLogging == "INFO":
            self.logging_level = logging.INFO
        else:
            self.logging_level = logging.WARNING
        logger.setLevel(self.logging_level)

        self.dt_server_url = config["dt_server_url"]
        self.api_token = config["api_token"]
        self.inputs = config["inputs"].split("\n")
        self.output = config["output"]
        self.formula = config["formula"]



    def query(self, **kwargs):
        
        requests.packages.urllib3.disable_warnings()

        logger.setLevel(self.logging_level)

        letters="ABCDEFGHIJ"
        repls = {}
        theExpression=self.formula

        # iterate over inputs
        for input in self.inputs:
          # get data for input metrics
          r = requests.get(
                          self.dt_server_url+'/api/v2/metrics/query',
                          params={
                            'metricSelector':input,
                            'resolution':'1m',
                            'from':'-2m'
                            }, 
                          headers={
                            'Authorization': "Api-Token " + self.api_token, 
                            'accept': 'application/json; charset=utf-8'
                            },
                          verify=False
                          )

          # error ?
          if(r.status_code != 200):
              logger.error(r.status_code, r.reason, r.text) 
              return
              
          logger.debug(r.text)
          
          # parse retrieved data as json
          jsonContent=json.loads(r.text)

          # extract value from json structure
          try:
            #timestamp = jsonContent["result"][0]["data"][0]["timestamps"][0]
            value = jsonContent["result"][0]["data"][0]["values"][0]
            if(value is not None):
              # build replacement set ( Letter, value )
              logger.info("Value retrieved : "+str(value))
              repls[letters[self.inputs.index(input)]]=str(value)
          except:
            logger.error("No value found for "+input)
          

      

        # replace all letters with corresponding values in the formula
        for r in repls:
          theExpression = theExpression.replace(r, repls[r])

        # compute the formula and handle errors
        try:
            result = evaluate(theExpression)
            # special case where the expression resolves as a boolean value
            if(result==True or result==False):
              # convet the value to 1 or 0
              result=int(result)
        except SyntaxError:
            # If the user enters an invalid expression
            logger.error("Invalid input expression syntax")
            return
        except (NameError, ValueError) as err:
            # If the user tries to use a name that isn't allowed
            # or an invalid value for a given math function
            logger.error(err)
            return

        logger.info("Result : "+str(result))


        # send result to Dynatrace
        r = requests.post(
            self.dt_server_url+'/api/v2/metrics/ingest', 
            data=self.output+" "+str(result),  #+" "+ timestamp,
            headers={
              'Authorization': "Api-Token " + self.api_token,
              'Content-Type': 'text/plain; charset=utf-8'
              },
            verify=False
            )

        # error ?
        if(r.status_code != 202):
            logger.error(r.status_code, r.reason, r.text) 
            return
        else:
            logger.debug(r.text)

