# 6. Identity and security

## What you learn

- The difference between authentication and authorization.
- What is in an access token, and how a logout stops it before it expires.
- How passwords are kept, and why login gives one answer for each failure.
- How a route asks for a token, and how a handler gets the user.
- Why a task of a different user gives 404, and how rate limits slow abuse.

## Concepts

### Authentication and authorization

**Authentication** answers "who are you?". **Authorization** answers "may you
do this?". A request with no valid token fails authentication: 401. A request
with a valid token for data of a different user is an authorization question.
This service answers it with 404, as chapter 5 showed: the repository looks
only at the tasks of the owner.

### The access token

Login gives a **JWT** (JSON Web Token), signed with HS256 and the secret
`IDENTITY_JWT_SECRET`. A JWT has three parts with dots between them: a header,
the claims, and a signature. The claims of this service:

| Claim | Meaning |
|---|---|
| `iss` | The issuer, `bustan-sample` |
| `sub` | The user id |
| `jti` | A unique id of this token |
| `iat`, `exp` | Issued at, expires at (15 minutes later by default) |

The server checks the signature, the issuer and `exp` on each request. It
accepts only HS256, so a token that says "algorithm none" is refused.

A signed token is valid until it expires, even after a logout. To stop it
sooner, logout puts its `jti` in a **revocation list**, and the authenticator
refuses each token in the list. A scheduled job removes the entries of
expired tokens each 10 minutes (chapter 7).

### Passwords

The service keeps only an **Argon2id** hash of each password. A hash takes tens
of milliseconds of CPU, so it runs on a worker thread and does not stop other
requests. For an unknown email, login still checks a dummy hash, and each
failure gives the same 401 message. A caller cannot learn which addresses have
an account from the answer or from its time.

### Auth on a route

bustan has a registry of **authenticators**. The identity module registers
one, `bearer`, which reads `authorization: Bearer <token>`:

```python
@Controller("/tasks")
@Auth("bearer")
class TasksController:
    async def list_tasks(self, user: Annotated[AuthenticatedUser, CurrentUser()], ...):
        ...
```

- `@Auth("bearer")` on a controller protects each route of it.
- `@Public()` on one route opens it (register and login).
- The guard puts the user on the request. `CurrentUser()` is a parameter
  marker that gives it to the handler as an `AuthenticatedUser`.
- The tasks module imports `IdentityModule` for the registry, and only the
  public names of identity.

### Rate limits

Each client gets 300 requests a minute, and 10 a minute on login and on
register (`@RateLimit(limit=10, window="1m")`). A refused request gets 429 and
`Retry-After`, and a refused request is not counted, so a caller that retries
too early does not make its own wait longer. The health probes are not
limited.

## Try it

1. Log in, and look inside the token:

   ```bash
   uv run python -c "import jwt, sys; print(jwt.decode(sys.argv[1], options={'verify_signature': False}))" "$TOKEN"
   ```

2. Log out, then use the same token again:

   ```bash
   curl -si -X POST http://127.0.0.1:3000/identity/logout -H "authorization: Bearer $TOKEN" | head -1
   curl -si http://127.0.0.1:3000/identity/me -H "authorization: Bearer $TOKEN" | head -1
   ```

   The first gives 204, the second 401.

3. Register a second user, `bob@example.com`, log in as Bob, and ask for the
   id of a task of Ada. You get 404, the same answer as for an id that does
   not exist.

4. Send 11 logins with a wrong password in one minute. The 11th gets 429.
   Read its `retry-after` header.

## Why it is built this way

- **JWT with a revocation list.** A JWT lets each process check a token with
  no database read, but a pure JWT cannot be stopped before it expires. The
  revocation list adds one read for each request and gives a real logout.
  The short lifetime keeps the list small. There is no refresh token: a
  client logs in again after 15 minutes.
- **404 for the data of others.** 403 would tell a caller that the id exists.
- **One storage for the rate limits.** bustan takes the storage of the
  throttler when Python imports the root module, before the database exists.
  So the root gives one `BackendThrottlerStorage` to the throttler, and
  `ThrottlingModule` binds it to the database at startup. With SQLite, all
  processes share the counts. The cost: two applications in one process share
  the storage, so run one application for each process.

## Check yourself

1. Why does the logout need a list on the server if the token is signed?
2. Why does login check a dummy hash for an unknown email?
3. A new route must be open to all. Which decorator do you add, and where?

Next: [7. Events, jobs and schedules](07-events-jobs-and-schedules.md).
