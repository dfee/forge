.. image:: https://raw.githubusercontent.com/dfee/forge/blob/master/docs/_static/logo.png
   :alt: forge logo

============================================
forge: (python) signatures for fun and profit
============================================

``forge`` is an elegant Python package that allows for meta-programming of function signatures. Tools like parameter conversion, validation, and typing are now trivial.


Key Features
===========================
- Revise function signatures by adding, removing, or adjusting parameters
- Convert and validate arguments
- Distinguish between user-supplied arguments and their default counterparts
- 100% tested (branches included)

Quickstart
==========

Re-signing a function
---------------------

The primary purpose of forge is to alter the public signature of functions:

.. code-block:: python

  import forge

  @forge.sign(
      forge.pos('positional'),
      forge.arg('argument'),
      *forge.args,
      forge.kwarg('keyword'),
      **forge.kwargs,
  )
  def myfunc(*args, **kwargs):
      return (args, kwargs)

.. code-block:: python

  >> help(myfunc)
  myfunc(positional, /, argument, *args, keyword, **kwargs)
  >>> args, kwargs = myfunc(1, 2, 3, 4, 5, keyword='abc', extra='xyz')
  >>> args
  (3, 4, 5)
  >>> kwargs
  {'extra': 'xyz', 'positional': 1, 'argument': 2, 'keyword': 'abc'}

You can re-map a parameter to a different type, and optionally supply a default value:

.. code-block:: python

  import forge

  @forge.sign(
      forge.keyword('colour', 'color', default='blue'),
  )
  def myfunc(colour):
    return colour

  >>> help(myfunc)
  myfunc(*, color='blue')
  >>> myfunc()
  'blue'

You can also supply type annotations for usage with linters like mypy:

.. code-block:: python

  import forge

  @forge.sign(
    forge.arg('number', annotation=int),
  )
  @forge.returns(str)
  def to_str(number):
      return str(number)

  >>> help(to_str)
  to_str(number:int) -> str
  >> to_str(3)
  '3'


Validating a parameter
----------------------

You can validate arguments by either passing a validator or an iterable (such as a list or tuple) of validators to your ParameterMap constructor.

.. code-block:: python

  import forge

  def validate_gt5(ctx, name, value):
      if value < 5:
          raise TypeError(f"{name} must be >= 5")

  @forge.sign(
      forge.arg('count', validator=validate_gt5)
  )
  def send_presents(count):
      print(f'sending {count} presents')

  >>> send_presents(3)
  TypeError: count must be >= 5
  >>> send_presents(5)
  sending 5 presents

You can optionally provide a context parameter, such as `self`, `cls`, or create your own named parameter with `forge.ctx('myparam')`, and use that alongside validation:

.. code-block:: python

  import forge

  def validate_color(ctx, name, value):
      if value not in ctx.colors:
          raise TypeError(f'expected one of {ctx.colors}, received {value}')

  class ColorSelector:
      def __init__(self, *colors):
          self.colors = colors
          self.selected = None

      @forge.sign(
          forge.self,
          forge.arg('color', validate_color)
      )
      def select_color(self, color):
          self.selected = color

  >>> cs = ColorSelector('red', 'green', 'blue')
  >>> cs.select('orange')
  TypeError('expected one of ('red', 'green', 'blue'), received 'orange')
  >>> cs.select('red')
  >>> print(cs.selected)
  red


Converting a parameter
----------------------

You can convert an argument by passing a conversion function to your ParameterMap constructor.

.. code-block:: python

  import forge

  def uppercase(ctx, name, value):
      return value.upper()

  @forge.sign(
      forge.arg('message', converter=uppercase)
  )
  def shout(message):
      print(message)

  >>> shout('hello over there')
  HELLO OVER THERE

You can optionally provide a context parameter, such as `self`, `cls`, or create your own named ParameterMap with `forge.ctx('myparam')`, and use that alongside conversion:

.. code-block:: python

  import forge

  def titleize(ctx, name, value):
      return f'{ctx.title} {value}'

  class RoleAnnouncer:
      def __init__(self, title):
          self.title = title

      @forge.sign(
          forge.self,
          forge.arg('name', converter=titleize)
      )
      def announce(self, name):
          print(f'Now announcing {name}!')

  >>> doctor_ra = RoleAnnouncer('Doctor')
  >>> patient_ra = RoleAnnouncer('Doctor')
  >>> doctor_ra.announce('Strangelove')
  Now announcing Doctor Strangelove!
  >>> captain_ra.announce('Lionel Mandrake')
  Now announcing Captain Lionel Mandrake!


Usage (Narrative)
=================
For example, consider the following `BaseService.update` method below:

.. code-block:: python

  class BaseService:
      def update(self, ins, **kwargs):
          for k, v in kwargs.items():
              setattr(ins, k, v)
          self.persist(ins)
          return ins

      def persist(self, ins):
          ...

Now, if we want to create a more specific implementation, e.g. `UserService`, and we want to allow certain parameters, we end up with code that looks like:

.. code-block:: python

  class UserService(BaseService):
      def update(self, ins, **kwargs):
          cleaned = {}
          if 'email_address' in kwargs:
              email_address = kwargs['email_address']
              if not re.search(r'\w+@\w+\.\w+', kwargs['email_address']):
                  raise TypeError('Email address doesn't conform to pattern')
              cleaned['email_address'] = kwargs['email_address']
          if 'name' in kwargs:
              cleaned['name'] = kwargs['name'].title()
          if 'manager' in kwargs:
              cleaned['manager'] = manager
          return super().update(ins, **cleaned)

This `update` method is nice enough, except that the signature doesn't exactly describe what parameters are accepted. Upon inspection (using `help(UserService.update`) we find out that the method takes two parameters: `self` and a variable-keyword argument `kwargs`. Is `profile_picture` accepted? NO! How about `password`? Absolutely not! There are special methods for those.

.. code-block:: python

  class UserService(BaseService):
      def update(self, ins, **kwargs):
          ...

      def set_password(self, ins, newpass):
          ...

      def set_profile_picture(self, ins, *, image_url=None, image_buf=None):
          ...

      def create(self, **kwargs):
          # and, what parameters would this take?
          # do we duplicate our validation code? our unit-tests?
          ...

So, we realize now that we need to do parameter conversion and validation in multiple places, so we need to extract that logic:

.. code-block:: python

  def validate_email_address(email_address):
    if not re.search(r'\w+@\w+\.\w+', kwargs['email_address']):
        raise TypeError('Email address doesn't conform to pattern')

  def convert_name(name):
      return name.title()

  class UserService(BaseService):
      def update(self, ins, **kwargs):
          cleaned = {}
          if 'email_address' in kwargs:
              validate_email_address(email_address)
              cleaned['email_address'] = kwargs['email_address']
          if 'name' in kwargs:
              cleaned['name'] = convert_name(kwargs['name])
          if 'manager' in kwargs:
              cleaned['manager'] = kwargs['manager']
          return super().update(ins, **cleaned)

      def create(self, ins, **kwargs):
          cleaned = {}
          ... # validate, convert as above
          return super().create(**kwargs)

Now, we're faced with the problem that our method still doesn't describe to a user what parameters it takes. Open up your python interpreter, and type `help(UserService.update)`.

Now, we can naively solve this problem by naming the parameters:

.. code-block:: python

  class UserService(BaseService):
      def update(self, *, email_address=None, name=None, manager=None):
          cleaned = {}
          if email_address is not None:
              validate_email_address(email_address)
              cleaned['email_address'] = email_address
          if name is not None:
              cleaned['name'] = convert_name(name)
          if manager is not None:
              cleaned['manager'] = manager
          return super().update(ins, **kwargs)

So now, our method signature adequately describes what parameters `UserService.update` takes. Except, what if a user actually becomes self-employed and no-longer has a manager. We've lost the ability to *unset* attributes, as our code can't distinguish between what arguments were provided as `None` by the user, and which arguments are `None` by default:

.. code-block:: python

  >>> user_service.update(newly_self_employed_user, manager=None)
  <User: name=Jane Doe, email_address=jane@janedoe.com, manager=Evil Bob>
  >>> # why can't Jane escape? why?!

Enter `forge`: to escape from the problems we faced above, namely the paradox of having a well defined signature impeding usage, we can use `forge`:

.. code-block:: python

  import forge

  class UserService(BaseService):
      @forge.sign(
          forge.self,
          forge.arg('ins'),
          email_address=forge.kwarg(validator=validate_email_address),
          name=forge.kwarg(converter=convert_name),
          manager=forge.kwarg(default=void),
      )
      def update(self, ins, **kwargs):
          return super().update(self, ins, **forge.devoid(**kwargs))

Reusing parameters across multiple functions isn't difficult, either:

.. code-block:: python

  import forge

  class UserService(BaseService):
      params = {
        'ins': forge.arg('ins'),
        'email_address': forge.kwarg(
            'email_address',
            validator=validate_email_address,
        ),
        'name': forge.kwarg('name', converter=convert_name),
        'manager': forge.kwarg('manager', default=void),
        'password': forge.kwarg(
            'password',
            validator=validate_password,
            converter=convert_password,
        ),
      }

      @forge.sign(
          forge.self,
          params['ins'],
          params['email_address'],
          params['name'],
          params['manager'],
      )
      def update(self, ins, **kwargs):
          return super().update(self, ins, **forge.devoid(**kwargs))

      @forge.sign(
          forge.self,
          params['password'],
          params['email_address'],
          params['name'],
          params['manager'].replace(default='Evil Bob'),
      )
      def create(self, **kwargs):
          return super().create(self, **forge.devoid(**kwargs))

      @forge.sign(
          forge.self,
          params['ins'],
          params['password'],
      )
      def set_password(self, ins, password):
          ins.password = password
          self.persist(ins)
          logout_user_from_active_sessions(ins)

And, if you are inspecting the method, what do you see?

.. code-block:: python

  >>> help(UserService.update)
  update(self, *, email_address=<void>, name=<void>, manager=<void>)

We've isolated parameter level validation and conversion, reducing boilerplate logic significantly, and our methods have meaningful signatures. Therefore, our code is easier to reason about and test, and developers who use are code can spend more time in their IDE or REPL environment than cross-referencing which parameters are available for a particular method.

So go on, `forge` some (function) signatures for fun and profit.


Advanced Usage
==============
You can use the `forge.Forger` class directly, which is very useful when you're decorating functions and want to side-load certain parameters.

Typically, the code we use today, looks like this:

.. code-block:: python

  import functools
  from types import SimpleNamespace

  class Context(SimpleNamespace):
      pass

  def get_context_from_somewhere():
      return Context()

  def add_context(func):
      @functools.wraps(func)
      def inner(*args, **kwargs):
          ctx = get_context_from_somewhere()
          return func(ctx, *args, **kwargs)
      return inner

  @add_context
  def myfunc(ctx, myparam, *, log=False):
      if log:
          print(ctx, '... with myparam: ', myparam)

  >>> myfunc(9000, log=True)
  Context() ... with myparam 9000
  >>> help(myfunc)
  mfunc(ctx, id, *, log=False)

You'll see that the function signature has preserved the `ctx` parameter, which is an implementation detail, and oughta be private to the function. If the user provides `ctx`...

.. code-block:: python

  >>> myfunc(ctx=Context(), myparam=1000)
  myfunc() got multiple values for argument 'ctx'

Users of the function aren't supposed to provide this functionality. Forge paves the way here (again).

.. code-block:: python

  import functools
  from types import SimpleNamespace

  import forge

  class Context(SimpleNamespace):
      pass

  def get_context_from_somewhere():
      return Context()

  def add_context(func):
      forger = forge.Forger.from_callable(func)
      forger.pop(0)

      @forger
      def inner(*args, **kwargs):
          ctx = get_context_from_somewhere()
          return func(ctx, *args, **kwargs)
      inner.__name__ = func.__name__
      inner.__doc__ = func.__doc__
      return inner

  @add_context
  def myfunc(ctx, myparam, *, log=False):
      if log:
          print(ctx, '... with myparam: ', myparam)

  >>> myfunc(9000, log=True)
  Context() ... with myparam:  9000
  >>> help(myfunc)
  myfunc(myparam, *, log=False)

Now, a casual user wouldn't even think to pass `ctx`.


Requirements
============

- Python >= 3.6


Author
=======

This package was conceived of and written by Devin Fee. Other contributors are listed under https://github.com/dfee/forge/graphs/contributors


License
=======

``forge`` is offered under the MIT license.


Source code
===========

The latest developer version is available in a github repository:
https://github.com/dfee/forge


Image / Meta
============
`Salvador Dali <https://en.wikipedia.org/wiki/Salvador_Dal%C3%AD>`_, a Spanish surealist artist, is infamous for allegedly forging his own work. In his latter years, it's said that he signed blank canvases and tens of thousands of sheets of lithographic paper (under duress of his guardians). In the image atop this `README`, he's seen with his pet ocelot, Babou. This image is recomposed from the original, whose metadata is below.

| **Title**: `Salvatore Dali with ocelot friend at St Regis / World Telegram & Sun photo by Roger Higgins <http://www.loc.gov/pictures/item/95513802/>`_
| **Creator(s)**: Higgins, Roger, photographer
| **Date Created/Published**: 1965.
| **Medium**: 1 photographic print.
| **Reproduction Number**: LC-USZ62-114985 (b&w film copy neg.)
| **Rights Advisory**: No copyright restriction known. Staff photographer reproduction rights transferred to Library of Congress through Instrument of Gift.
| **Call Number**: NYWTS - BIOG--Dali, Salvador--Artist <item> [P&P]
| Repository: Library of Congress Prints and Photographs Division Washington, D.C. 20540 USA