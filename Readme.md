#Patsy HTTP 1.0 webserver

##Introduction

[Patsy](http://en.wikipedia.org/wiki/Patsy_%28Monty_Python%29) is named 
after the King Arthur's assistant in the film "Monty Python and The Holy Grail".

It is a simple HTTP 1.0 webserver implemented in Python 3 for educational
purposes. It implements most of [RFC 1945](http://tools.ietf.org/rfc/rfc1945.txt).

In particular it can serve GET and HEAD requests. It returns 501 Not Implemented
in case of POST requests.

Remember that patsy wasn't written with performance or security in mind. Do not
use it in production environments.

##Patsy Anatomy

Patsy essential files are the patsy executable patsy.py. The directory
messages which contains the text/html bodies of the status codes responses, 
such as the response html returned from a 404 Not Found. The accesslist.json
which is a json file containing directories under the document root that
are password protected. Finally an htdocs directory which will contain the
files that patsy will serve.

These directories and files don't have a particular place in the filesystem
but patsy should have read access and be properly configured to use them.

##Configuring Patsy

Patsy is easy to get configured. There is a list named CONFIGURATION that
holds all the essential information that patsy requires. Let's see the available
options in detail.

 * HOST : This is the IP address that patsy will bind to. If 0.0.0.0 is used then
 it will bind to all interfaces. This is the preferred option.
 * PORT : This is the port that patsy will listen for requests. You can use
 whatever it pleases you. 80 or 8080 are the popular choices.
 * MAX_REQUEST : This is the maximum request size that patsy will expect.
 It is set in 4 KB by default which is more than enough for GET or HEAD requests.
 If the whole request body exceeds MAX_REQUEST then patsy returns an 413
 Request Entity Too Large as specified in RFC 2068(this is the only return status
 returned that isn't specified in RFC 1945).
 * DOCUMENT_ROOT : This is the directory where the documents served by patsy
 reside. This can be a relative to patsy executable path or an absolute path
 which is preferred. If this path is misconfigured patsy will silently fail
 and every valid request will return a 404 Not Found reply.
 * HTTP_VERSION : This is a string with the supported HTTP version. In some cases
 it may be returned to the client. In most cases you don't have to change that.
 * MESSAGES_PATH : This the path to the directory which contains the message
 files. Message files contain the status code message body, i.e. in 404 Not Found
 it contains the html message that the browser will display. The path must be
 relative to patsy executable or absolute which is the preferred way. In case
 of misconfiguration patsy will raise a file not found exception. Message bodies
 may contain some values that are retrieved from the server dynamically.
 This can be for example the date or the server's port number. See the messages
 distributed with patsy for examples. Messages directory also contain
 the dir-list-top.html and dir-list-bottom.html which are used when patsy
 returns the list of all the files in a directory.
 * SERVER : This is a string with the server's name. In most cases there isn't
 need to change it.
 * FROM : The given string is used for the From request-header field. See
 10.8 From in RFC 1945. If this value is empty patsy won't return a FROM
 field at all.
 * DEFAULT_INDEX : This is a list with filenames that patsy will server
 if they exist in a directory, when the request URL requests that directory.
 index.html is an example.
 * ACCESSLIST : This is a json file that contains directories or files that
 patsy will require a password in order to serve. See the provided accesslist.json
 about the syntax. As always, path can be relative to patsy executable or
 absolute which is the preferred way. If this path is misconfigured patsy will
 raise an exception at the startup as it loads this file once only then.
 
##Status Codes

Here are the return values that patsy supports and may return:

 * 200 OK
 * 301 Moved Permanently
 * 304 Not Modified
 * 400 Bad Request
 * 401 Authorization
 * 403 Forbidden
 * 404 Not Found
 * 413 Request Entity Too Large
 * 501 Not Implemented
 
More about these status codes in RFC 1945 (or 2068).

##Performance

As said, patsy wasn't written with performance in mind. Some simple
tests that I have run with ab suggest that patsy is at least 5 times
slower than Apache httpd with somewhat default configuration. Patsy
may be much slower in more complex tasks.

##Other Notes

You should have Python 3 in order to run patsy. You shouldn't need any
root privileges. I have tested patsy only in Linux. I do not recall
any os specific code but I cannot really tell if you will face any problems
if you try to run it on some other platform.

Patsy is licensed under the MIT License and written by Periklis Ntanasis.
