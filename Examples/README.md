# Examples

A small collection of examples uses for pulpy.


## pulpy2ban

Inspired by [Fail2Ban](https://www.fail2ban.org/wiki/index.php/Main_Page) this examples blocks all requests from a source that was deemed to be "malicious" for x amount of time where x increase exponentially every time a "malicious" request occurs.

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

## Shower

This simulates multiple showers and multiple users trying to adjust the temperatures to their preferred temperatures. Each user can have access to any amount of the showers.

Users can only say hotter or colder, additionally, they have to work against others' wishes if they have different preferred temperatures.

If they all agree, or are close to agreeing, on the ideal temperature this usually settles itself relatively quickly: 

![](gifs/shower_consensuas.gif)

Unlike when they do not:

![](gifs/shower_no_consensuas.gif)

To run:

```$ python shower.py```

with graph:

```$ python shower.py -g```

with close preferred temperatures:

```$ python shower.py -c```


## Web Search

A highly simplified "web search". 

1. Sources send requests to the load balancer. 
2. The load balancer sends requests randomly to frontend servers. 
3. If the frontend server has the requested item, it will complete the job.
4. Then the frontend server requests an item in each backend servers' memory. 
5. Once the frontend server has all backend responses it sends it directly to the original request source.

To run:

```$ python webSearch.py```

with graph:

```$ python webSearch.py -g```

![](gifs/webSearch.gif)

## Periodic

Periodic uses the PeriodicSource class to generate for every item a request every x time units where x is chosen randomly. 

to run:

```$ python periodic.py ```





