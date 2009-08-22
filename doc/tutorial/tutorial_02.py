
def say_something(times, text):
    output = open("hey_python.txt","w")
    output.write(times * text)
    output.close()
    return True


def task_hello_python():
    return {'action':say_something,
            'args':(10,),
            'kwargs':{'text':'hey! '}}

def task_hi_sh():
    hi = 10 * "hi! "
    return {'action':"echo '%s' > hi_sh.txt"% hi}
