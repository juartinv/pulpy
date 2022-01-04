# Examples


## pulpy2ban

Inspired by [Fail2Ban](https://www.fail2ban.org/wiki/index.php/Main_Page) this examples blocks all requests from a source that was deemed to be "malicous" for x amount of time where x increase exponentially everytime a "malicous" request occurs.

to run:


```$ python pulpy2ban.py ```

## One-hop DHT



A one hop dht (highly simplified), inspired by [One-hop](https://www.usenix.org/legacy/events/hotos03/tech/full_papers/gupta/gupta_html/). 

Each machine is responsible for an ID range and if a request is not for their id the machine will forward it to the correct machine.

Each machine knows the location of all other machines.

to run:


```$ python oneHop.py ```

### Valiantly routing One-hop DHT

To turn your One-hop DHT to a \<valiant\> many random hops prior system run:


```$ python oneHop.py v=<valiant>```

ex.


```$ python oneHop.py v=1```  
	--> sends requests to one random machine prior to the correct one.
	

## Periodic

Periodic uses the PeriodicSource class to generate for every item a request every x time units where x is chosen randomly. 

to run:

```$ python periodic.py ```

## Shower

todo

## Web Search

Todo


