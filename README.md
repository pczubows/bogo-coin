# Bogo Coin

Simulated network of cryptocurrency nodes. Each node is implemeneted as a Flask app equipped with blockchain and simple request verification. Apps have ability to register with one another as peers and then communicate about new peers and transactions in the network.

Each app can also accept schedule file as an arguemnt. Schedule file is specially formatted text file which specifies actions that app will perform during simulation. The precise formatting of schedule file commands is specified in [```coin.TestScheduler```](../master/coin/test_scheduler.py) docstrings.

## Usage

```app.py [-h] [-p PORT] [-G] [-v] [-s SCHEDULE] [-a ACCUMULATION] [-T THROTTLE]```

optional arguments:
  ```-h, --help```            show argsparse generated help 
  ```-p PORT, --port PORT```  specify port on which app will listen, defaults to 5000
  ```-G, --genesis```         inintiate node with genesis block
  ```-v, --verbose```         display info level log, otherwise only bare flask logs will be printed
  ```-s SCHEDULE, --schedule SCHEDULE``` path to test schedule file
  ```-a ACCUMULATION, --accumulation ACCUMULATION ``` time in seconds app waits before it starts to mine transactions into new block, defaults to 0.5s  
  ```-T THROTTLE, --throttle THROTTLE``` arbitrary slowdown of mining speed 

### Test Scenarios 

Example test scenarios are located in [```test_scenarios```](../master/test_scenarios) directory. Each subdirectory contains test schedule files and bash script for launching whole network and gathering node states at the end of simulation. [```normal```](../master/test_scenarios/normal) subdirectory contains network working without any nodes attempting to forge blockchain. In [```forge```](../master/test_scenarios/forge) there are two scenarios where single node tries to replace chain with fake one. One in which all nodes have same mining speed and one where "evil" node is much faster than others.

## Requirements

Python 3.6+ Modules: Flask, requests, cryptography

## Based on

* [https://github.com/dvf/blockchain](https://github.com/dvf/blockchain)
* [https://medium.freecodecamp.org/the-authoritative-guide-to-blockchain-development-855ab65b58bc](https://medium.freecodecamp.org/the-authoritative-guide-to-blockchain-development-855ab65b58bc)
