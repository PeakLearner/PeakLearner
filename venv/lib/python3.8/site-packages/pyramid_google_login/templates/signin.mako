<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sign in</title>

  <link rel="stylesheet"
        href="${request.static_url('pyramid_google_login:static/pure-min.css')}">
  <link rel="stylesheet"
        href="${request.static_url('pyramid_google_login:static/login.css')}">
</head>
<body>

  <div class="splash-container">
    <div class="splash">

% if signin_banner:
      <p class="splash-head">
        ${signin_banner}
      </p>
% endif

      <p>
        <a href="${signin_redirect_url}" class="pure-button pure-button-primary">
          Sign in
        </a>
      </p>

      <p class="splash-message">
% if signin_advice:
        ${signin_advice}
% elif hosted_domain is not None:
        Please sign in with your ${hosted_domain} account
% else:
        Please sign in with your Google account
% endif
      </p>

% if message:
      <p class="splash-error">
        ${message}
      </p>
% endif

    </div>
  </div>

</div>

</body>
</html>
