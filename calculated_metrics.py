"""
 curl -X GET "https://ure00800.live.dynatrace.com/api/v2/metrics/query?metricSelector=calc%3Aservice.numberoffindlocations&resolution=1m&from=-2m" 
      -H "accept: application/json; charset=utf-8" 
      -H "Authorization: Api-Token 6DZoDNw1Qrm7HFaU-3Drk"

OK=200 

{
  "totalCount": 1,
  "nextPageKey": null,
  "result": [
    {
      "metricId": "calc:service.numberoffindlocations",
      "data": [
        {
          "dimensions": [
            "SERVICE-58FA85926F0D9BB9",
            "All requests"
          ],
          "dimensionMap": {
            "dt.entity.service": "SERVICE-58FA85926F0D9BB9",
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



curl -X GET "https://ure00800.live.dynatrace.com/api/v2/metrics/query?metricSelector=calc%3Aservice.numberoffindjourneys&resolution=1m&from=-2m" 
     -H "accept: application/json; charset=utf-8" 
    -H "Authorization: Api-Token 6DZoDNw1Qrm7HFaU-3Drk"

OK = 200

     {
  "totalCount": 1,
  "nextPageKey": null,
  "result": [
    {
      "metricId": "calc:service.numberoffindjourneys",
      "data": [
        {
          "dimensions": [
            "SERVICE-58FA85926F0D9BB9",
            "All requests"
          ],
          "dimensionMap": {
            "dt.entity.service": "SERVICE-58FA85926F0D9BB9",
            "Dimension": "All requests"
          },
          "timestamps": [
            1616766540000,
            1616766600000,
            1616766660000
          ],
          "values": [
            42,
            10,
            null
          ]
        }
      ]
    }
  ]
}


curl -X POST "https://ure00800.live.dynatrace.com/api/v2/metrics/ingest" 
     -H "accept: */*" 
     -H "Authorization: Api-Token 6DZoDNw1Qrm7HFaU-3Drk" 
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

        logger.setLevel(self.logging_level)

        letters="ABCDEFGHIJ"

        repls = {}

        # iterate over inputs
        # for each
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
                            }
                          )

          # error ?
          if(r.status_code != 200):
              logging.error(r.status_code, r.reason, r.text) 
              return
              
          
          logging.debug(r.text)
          
          jsonContent=json.loads(r.text)

          value=""
          try:
            #timestamp = jsonContent["result"][0]["data"][0]["timestamps"][0]
            value = jsonContent["result"][0]["data"][0]["values"][0]
            if(value is not None):
              repls[letters[self.inputs.index(input)]]=str(value)
          except:
            logger.error("No value found for "+input)
          

      

        # replace all letters with corresponding values in the formula
        for r in repls:
          self.formula = self.formula.replace(r, repls[r])

        # compute the formula and handle errors
        try:
            result = evaluate(self.formula)
        except SyntaxError:
            # If the user enters an invalid expression
            logger.error("Invalid input expression syntax")
            return
        except (NameError, ValueError) as err:
            # If the user tries to use a name that isn't allowed
            # or an invalid value for a given math function
            logger.error(err)
            return



        # send result to Dynatrace
        r = requests.post(
            self.dt_server_url+'/api/v2/metrics/ingest', 
            data=self.output+" "+str(result),  #+" "+ timestamp,
            headers={
              'Authorization': "Api-Token " + self.api_token,
              'Content-Type': 'text/plain; charset=utf-8'},
            verify=False
            )

        # error ?
        if(r.status_code != 202):
            logging.error(r.status_code, r.reason, r.text) 
            return
        else:
            logging.debug(r.text)


def main():
  params={
    "config":{
        "dt_server_url": "https://ure00800.live.dynatrace.com",
        "api_token": "6DZoDNw1Qrm7HFaU-3Drk",
        "inputs": "calc:service.numberoffindjourneys\ncalc:service.numberoffindlocations",
        "output": "ratio.sample",
        "formula": "(A/B)*100",
        "debug": "DEBUG"
        }
      }

  g=Generator()

  g.initialize(params)
  g.query()

if __name__ == "__main__":
    # execute only if run as a script
  main()
