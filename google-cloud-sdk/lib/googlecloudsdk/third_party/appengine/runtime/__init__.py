#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.

"""Define the DeadlineExceededError exception."""




# Python 2.4 doesn't have BaseException; in that case alias it to Exception.
try:
  BaseException
except NameError:
  BaseException = Exception


class DeadlineExceededError(BaseException):
  """Exception raised when the request reaches its overall time limit.

  This exception will be thrown by the original thread handling the request,
  shortly after the request reaches its deadline. Since the exception is
  asynchronously set on the thread by the App Engine runtime, it can appear
  to originate from any line of code that happens to be executing at that
  time.

  If the application catches this exception and does not generate a response
  very quickly afterwards, an error will be returned to the user and
  the application instance may be terminated.

  Not to be confused with runtime.apiproxy_errors.DeadlineExceededError.
  That one is raised when individual API calls take too long.
  """

  def __str__(self):
    return ('The overall deadline for responding to the HTTP request '
            'was exceeded.')
