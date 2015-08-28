from enum import Enum

#Each term is a dictionary with dbName, colName, searchValue, compareFunc

class NASSSearchJoin(Enum):
    AND = 0
    OR = 1
 
#A heirarchical node type object that holds all the parameters of a search
#Terms are the terms used to search, inverse is a logical not on this specific term
#The object is meant to be immutable so try not to go poking around the values
class NASSSearchTerm():
    #Terms can be two things
    #1) A dict containing dbName, colName, searchValue, and compareFunc
    #2) An odd length tuple of (term, join, term, join, term ...)
    # In this tuple a term is anoter NASSSearchTerm. A join is a value of NASSSearchJoin enum
    def __init__(self, terms, inverse=False):
        self.terms = terms
        self.inverse = inverse
        self.errorCheck()
    
    def __str__(self):
        return self.toStrList().__str__()
    
    def __eq__(self, other):
        return self.__hash__() == other.__hash__()
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        if isinstance(self.terms, dict):
            return (frozenset(self.terms.items()), self.inverse).__hash__()
        elif isinstance(self.terms, tuple):
            return (self.terms, self.inverse).__hash__()
            
    #Error checks term and all subterms
    def errorCheck(self):
        terms = self.terms
        #Error check dictionary
        if isinstance(terms, dict):
            keys = terms.keys()
            if len(keys) != 4 or not ("dbName" in keys and "colName" in keys and "searchValue" in keys and "compareFunc" in keys):
                raise ValueError("Dictionary for search term did not contain the right terms")
        #Error check tuple
        elif isinstance(terms, tuple):
            if len(terms) == 0:
                raise ValueError("No search terms were given")
            if len(terms) == 1:
                raise ValueError("Only one search term given. Do not create tuples containing one term.")
            if len(terms) % 2 != 1:
                raise ValueError("Search must contain an odd number of terms")
            termCount = 0
            for term in terms:
                #Even Term
                if termCount % 2 == 0 and not isinstance(term, NASSSearchTerm):
                    raise ValueError("Even term was not a search term")
                #Odd Term
                elif termCount % 2 == 1 and not isinstance(term, NASSSearchJoin):
                    raise ValueError("Odd term was not a join term")
                #Recursive check
                if isinstance(term, NASSSearchTerm):
                    term.errorCheck()
                
                termCount += 1
        #Other types are not allowed
        else:
            raise ValueError("Terms was not a dict or a tuple")
    
    #Returns all the distinct (terms containing terms of just one DB) terms from a DB or dbName
    #Tries to keep large terms consisting of one DB together
    #This function is recursive
    def ofDB(self, dbName):
        #If it's just a dict term, it's simple
        if isinstance(self.terms, dict):
            if self.terms["dbName"] == dbName:
                return set([self])
            else:
                return set()
        
        #Tuple of terms is harder
        #Once we find any chunk that's not of the DB, this entire term becomes not a largeTerm.
        #If all the terms are of largeTerm, it returns itself (because it's all made up of the same DB)
        elif isinstance(self.terms, tuple):
            largeTerm = True 
            dbTerms = set()
            for term in self.terms:
                #Joiner
                if isinstance(term, NASSSearchJoin):
                    continue
                #More child terms    
                elif isinstance(term, NASSSearchTerm):
                    childTerms = term.ofDB(dbName)
                    #If the child term does not equal the returned set, it is 
                    if len(childTerms) != 1:
                        largeTerm = False
                        
                    dbTerms = dbTerms.union(childTerms)
                    continue
                
            if largeTerm:
                return set([self])
            else:
                return dbTerms
    
    #Compares a term to a list of kvs of colName->rowValue
    def compare(self, kvs):
        #Func for mapping of NASSSearchTerms to some other value
        def mapFunc(term):
            #Dict term can be compared
            if isinstance(term.terms, dict):
                if not term.terms["colName"] in kvs: #Column wasn't in the dict, wat?
                    raise ValueError("Term compared to kv that didn't contain column described in search (wrong DB row compared?)")
                value = kvs[term.terms["colName"]]
                return term.terms["compareFunc"](value, term.terms["searchValue"])
            #List terms need more work
            elif isinstance(term.terms, list):
                return term.resolve(mapFunc, joinFunc)
        
        #Func for joining mapped values based on a join
        def joinFunc(firstTerm, join, secondTerm):
            if join == NASSSearchJoin.AND:
                return firstTerm and secondTerm
            elif join == NASSSearchJoin.OR:
                return firstTerm or secondTerm

        finalMatch = self.resolve(mapFunc, joinFunc)
        
        #The '^' is XOR. Return finalMatch or inverse of it
        return self.inverse ^ finalMatch
    
    #Resolve this list to a single term based on a mapping of terms to values (mapFunc) and a description on how to join them (joinFunc)
    #Will not modify the object in any way and uses separate lists to keep track of the entire term (kind of how toStrList works) in local scope
    #This function is indirectly recursive in that the mapFunc usually calls resolve again to work on child terms of a large term
    def resolve(self, mapFunc, joinFunc):
        if isinstance(self.terms, dict):
            return mapFunc(self)
        elif isinstance(self.terms, tuple):
            #1)Replace each term with resolved term
            resolvedList = []
            for term in self.terms:
                if isinstance(term, NASSSearchJoin):
                    resolvedList.append(term)
                else:
                    resolvedList.append(mapFunc(term))
                
            #2)Perform the operations on the terms described by the logical joins
            #We made a list of [resolved, joiner, resolved, joiner, resolved ...]
            #Resolve the operators by precedence.
            newResolvedList = []
            lastJoin = None
            precedence = [(NASSSearchJoin.AND,), (NASSSearchJoin.OR,)]
            for ops in precedence:
                newResolvedList = []
                for resolvedTerm in resolvedList:
                    #Joiner
                    if isinstance(resolvedTerm, NASSSearchJoin):
                        #Store last join if it's in this precedence pass, otherwise append for later
                        if resolvedTerm in ops:
                            lastJoin = resolvedTerm
                        else:
                            newResolvedList.append(resolvedTerm)
                        continue
                    #resolvedTerm
                    else:
                        #If there's a lastJoin take the current term and compare to the last and put that on
                        if lastJoin != None:
                            #Append the result of firstTerm JOIN secondTerm where
                            #firstTerm is the previous term in the list
                            #JOIN is the lastJoin recorded (and not appended into the list)
                            #secondTerm is this currently held term
                            joinedTerm = joinFunc(newResolvedList.pop(), lastJoin, resolvedTerm)
                            newResolvedList.append(joinedTerm) 
                            lastJoin = None
                        #Otherwise just append
                        else:
                            newResolvedList.append(resolvedTerm)
                
                #At the end of an operator, set the new list to be the one resolved now
                resolvedList = newResolvedList
                
            return resolvedList[0]
    
    #Instead of forming a search term with dicts, tuples and the above classes, a term can be formed from
    #1) A 4 or 5 tuple (["NOT"], dbName, colName, searchValue, compareFunc) for a single dict term
    #2) A list of the form [["NOT"], term, joinerString, term, joinerString, term ...] where terms are more 4/5 tuples or lists
    #The "NOT"s are optional in both cases to invert certain strings
    #JoinerString is a string representation of NASSSearchJoin
    @classmethod
    def fromStrList(cls, stringTerms):
        inverse = False
        if stringTerms[0] == "NOT":
            inverse = True
            stringTerms = stringTerms[1:]
        
        #Single tuple term become dict terms
        if isinstance(stringTerms, tuple):
            dictTerm = {
                "dbName" : stringTerms[0],
                "colName" : stringTerms[1],
                "searchValue" : stringTerms[2],
                "compareFunc" : stringTerms[3]
            }
            return NASSSearchTerm(dictTerm, inverse=inverse)
        #Lists of multiple terms become tuple terms
        elif isinstance(stringTerms, list):
            terms = []
            for term in stringTerms:
                if isinstance(term, str):
                    terms.append(NASSSearchJoin[term])
                else:
                    terms.append(cls.fromStrList(term))
            return NASSSearchTerm(tuple(terms), inverse=inverse)
        
    def toStrList(self):
        if isinstance(self.terms, dict):
            out = (self.terms["dbName"],
                    self.terms["colName"],
                    self.terms["searchValue"],
                    self.terms["compareFunc"])
        elif isinstance(self.terms, tuple):
            out = ["NOT"] if self.inverse else []
            for term in self.terms:
                if isinstance(term, NASSSearchJoin):
                    termStr = str(term)
                    dotPos = termStr.find(".")
                    termEnd = termStr[dotPos+1:]
                    out.append(termEnd)
                else: #isinstance(term, NASSSearchTerm):
                    out.append(term.toStrList())
                    
        return out

#A term is stateless but describes exactly what we need from each database and how it relates
#NASSSearch continues to collect data from each subsequent search and how it relates to the original terms and
#resolves it all down to the final cases        
class NASSSearch():
    def __init__(self, term):
        self.search = term
        self.searchData = {} #Dictionary of terms to sets of cases
    
    def ofDB(self, dbName):
        return self.search.ofDB(dbName)
    
    def fromDB(self, data):
        self.searchData.update(data)
    
    #Take the collected searchData (terms from self.search mapped to datasets) and
    #compute the final dataset
    def finalize(self):        
        #Func for mapping of NASSSearchTerms to some other value
        def mapFunc(term):
            if not term in self.searchData:
                if isinstance(term.terms, dict):
                    #Woah, that's not good, we found a singular term that didn't match.
                    #It has no more children so it's not like it was a non-distinct term.
                    #We must be missing some data in the search.
                    raise RuntimeError("Term with no matching data in NASSSearch. Missed a DB query?")
                else:
                    #A term that wasn't found just may be non-distinct
                    return term.resolve(mapFunc, joinFunc)
            else:
                #The actual resolution
                return self.searchData[term]
        
        #Func for joining mapped values based on a join
        def joinFunc(firstTerm, join, secondTerm):
            if join == NASSSearchJoin.AND:
                return firstTerm.intersect(secondTerm)
            elif join == NASSSearchJoin.OR:
                return firstTerm.union(secondTerm)
                
        return self.search.resolve(mapFunc, joinFunc)
    
        