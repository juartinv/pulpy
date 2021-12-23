# Auxiliary
def goodness(x,y):
    xx = x-np.average(x)
    yy = y-np.average(y)

    A = np.sqrt(np.inner(xx,xx))
    B = np.sqrt(np.inner(yy,yy))

    return np.inner(xx/A,yy/B)

def argminrnd(items, target):
    # Returns the argmin item. if there are many, returns one at random.
    # items and target must be the same length
    candidates = np.where(target == target.min())[0]
    return items[random.choice(candidates)]

def argmaxrnd(items, target):
    return argminrnd(items, -target)


def gen_values(size, a=1, b=100, normalize=False, sort=False, \
                desc=False, power=False, alpha = 2):
    # useful function to generate discrete linear and potential (power) distributions.
    # Generates values for various initializations.

    if not power:
        x = np.array(list(map(lambda x: random.randint(a,b),range(size))))
    else:
        x = np.exp(alpha*np.array(list(map(lambda x: random.expovariate(1),range(size)))))

    if normalize:
        # Ensure x adds up to 1
        x = x/x.sum()

    if sort:
        x = np.sort(x)
        # Note: defaults to quicksort, worstcase O(n**2).
        # check https://numpy.org/doc/stable/reference/generated/numpy.sort.html
        if desc:
            x = x[::-1]

    return x

# p = gen_values(M, normalize=True, sort=True, desc=True, power=True, alpha = 0.75)



# Miscellaneous
# colored text and background
def print_red(text): print("\033[91m {}\033[00m" .format(text))
def print_green(text): print("\033[92m {}\033[00m" .format(text))
def print_yellow(text): print("\033[93m {}\033[00m" .format(text))
def print_purple(text): print("\033[94m {}\033[00m" .format(text))
def print_cyan(text): print("\033[96m {}\033[00m" .format(text))
def print_gray(text): print("\033[97m {}\033[00m" .format(text))
