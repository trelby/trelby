import heapq

class node:
    def __init__(self, freq = 0, val = None):
        self.left = None
        self.right = None
        self.freq = freq
        self.val = val

    def __cmp__(self, other):
        return self.freq - other.freq
    
# generates an optimal huffman code for representing the items given.
# 'items' must be a map of values to be coded that have at least a .val
# member, containing the value to be coded, and a .freq member, giving the
# frequency of that value. the map must be keyed on the .val member. on
# output each item shall have acquired a .code member, giving the huffman
# code in (0|1)+ string notation. 
#
# this algorithm is based on the one in "Introduction to algorithms",
# 1990, by Cormen, Leiserson and Rivest, section 17.3.
def huffmanize(items):
    if len(items) == 0:
        return
    elif len(items) == 1:
        items.values()[0].code = "0"
        
        return

    Q = []
    for it in items.values():
        heapq.heappush(Q, node(it.freq, it.val))
    
    for i in range(len(Q) - 1):
        z = node()
        
        z.left = heapq.heappop(Q)
        z.right = heapq.heappop(Q)
        z.freq = z.left.freq + z.right.freq
        
        heapq.heappush(Q, z)

    root = heapq.heappop(Q)

    storeResult(root, items, "")

def storeResult(node, items, code):
    if node.left:
        storeResult(node.left, items, code + "0")
        storeResult(node.right, items, code + "1")
    else:
        items[node.val].code = code
