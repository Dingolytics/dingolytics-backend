from flask import g, redirect, render_template, request, url_for
from flask_login import login_user
from wtforms import Form, PasswordField, StringField, validators
from wtforms.fields import EmailField

from redash import settings
from redash.authentication.org_resolving import current_org
from redash.handlers.base import routes
# from redash.models import Group, Organization, User


class SetupForm(Form):
    name = StringField("Name", validators=[validators.InputRequired()])
    email = EmailField("Email Address", validators=[validators.Email()])
    password = PasswordField("Password", validators=[validators.Length(6)])
    org_name = StringField("Organization Name", validators=[validators.InputRequired()])
    # security_notifications = BooleanField()
    # newsletter = BooleanField()


@routes.route("/setup", methods=["GET", "POST"])
def setup():
    """
    Initial setup handler.

    If no organization exists, this handler will create a default
    organization and user based on the form data.

    If an organization exists, the user will be redirected
    to the index page.

    Check the `setup_default_org` and `setup_default_user` methods
    of the `DynamicSettings` class for more information on how the
    setup is done.

    TODO: Customise SetupForm via the DynamicSettings class.
    """
    if bool(current_org) or settings.S.MULTI_ORG:
        return redirect("/")

    form = SetupForm(request.form)
    # form.newsletter.data = True
    # form.security_notifications.data = True

    if request.method == "POST" and form.validate():
        default_org, default_groups = settings.D.setup_default_org(
            form.org_name.data,
        )
        user = settings.D.setup_default_user(
            org=default_org,
            group_ids=[group.id for group in default_groups],
            **form.data
        )
        g.org = default_org
        login_user(user)
        return redirect(url_for("redash.index", org_slug=None))

    return render_template("setup.html", form=form)
