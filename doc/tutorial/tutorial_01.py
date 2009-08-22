

def say_hello():
    output = open("hello_python.txt","w")
    output.write("Hello World.")
    output.close()
    return True


def task_hello_python():
    return {'action':say_hello}

def task_hello_sh():
    return {'action':"echo 'Hello World' > hello_sh.txt"}
