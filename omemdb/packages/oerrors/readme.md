# oerrors

## FAQ

### when should I use a oerror ?

Suppose that you are developing the package pypack, considering the two following persona:
* developer developing an other package (otherpy), based on pypack
* user of pypack or otherpy (engineer, or web_app that is used by an engineer)

All the errors that you may want to explain to the user must be oerrors. No need to make oerrors for the developer.

### ok, I have created oerrors for the user, but I need to create a few specific errors for the otherpy developer

You can use oerrors framework, it implements python errors interface so I see no drawbacks.

### I want to create an oerror, but I am lost.

First question : what is the context of the error. Is it relative to an object ? An action ?
When context has been identified, create a file named oerrors_context.py at the correct place. All necessary errors and 
functions for this context will be imported there.

Create specific errors, using oerrors errors. You may subclass existing errors, or create new ones.

A good practice is to have a centralized get_instance function inside the file. It is also often useful to create 
functions that are able to create an error with a minimum information (for example, class method 
.from_record(record, field)) that will create an error with the correct instance and error message).

Each time you will have to raise an error in the same context, you will use the same file.

### What are OExceptionCollections for ?

Sometimes, you may be able to gather several errors before raising them, which is better for user (instead of having 
errors one by one). To do this, you collect errors in OExceptionCollection, and raise at the end :

    oec = OExceptionCollection()
    for i in range(5):
        with oec.catch_errors():
            # perform action that may raise an OException
            action(i)
    # raise if error
    oec.raise_if_error()
    
### Ok. Can I use oerrors framework for warnings ?

Yes.
Even if your code doesn't raise, you may want to collect warnings. You can do this in oerrors.


### How do I manage warnings ?

First of all, you must decide which of your functions must implement the report interface. If a function may generate 
warnings without raising, then it must.
Try to have a few as possible functions that implement this interface, because it is quite tedious to code.

Here is an example of a function implementing the report interface:

    def fct(arg1, arg2, report=None, warn=True):
        # always start by creating a report
        report = OExceptionCollection() if report is None else report
        # now ensure that:
        # 1. errors will be attached to report
        # 2. a warning will be issued to user if relevant
        with report.catch_errors(raise_if_error=True, warn=warn):
            # perform actions
            a = calculation1()
            
            # you may raise if problem
            if a is None:
                raise oerrors_context_a.ValueError("/a", "wrong value")
                
            # if you call another function implementing the report interface,
            # always call it with the current report and warn=False
            b = calculation2(report=report, warn=False)
            
            return a * b


### Won't the instances of a report be incoherent if it gathers errors/warnings from different contexts ?

Yes they will. Ideally, when possible, try to work on one context only. If you don't have the choice (for example
complex workflows), you can use chapters.
A chapter will prepend "/chapter_name" to instances added to the chapter. If you attach one context to one chapter, your 
report will be well organized.

Two ways to work with chapters:

    # if you want to catch errors:
    with oec.catch_errors(within_chapter="context_a") as context_a_report:
        # perform operations
        ...
        
    # or if you just want to work in a chapter, without catching errors
    with oec.within_chapter("context_a") as context_a_report:
        # perform operations
        ...
