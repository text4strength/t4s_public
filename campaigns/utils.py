from django.core.mail import send_mail
from django.conf import settings


def send_email_notification(subject, msg_body):
    try:
        send_mail(subject, msg_body, settings.DEFAULT_FROM_EMAIL, [settings.SERVER_EMAIL, settings.TONY_EMAIL],
                  fail_silently=False)
    except Exception, e:
        raise e
    return

def copy_tree(parent_message, composer):
    """
    Copy the whole tree and return the root message
    """
    options = parent_message.options.all()

    # create a copy of parent message
    parent_message_groups = parent_message.groups.all()
    # once we set this to None, parent_message's fields like "groups", "composers" are gone, so we need to back up the groups above
    parent_message.pk = None
    parent_message.composer = composer
    parent_message.save() # otherwise, we get this error: "<Message: Hello>" needs to have a value for field "message" before this many-to-many relationship can be used

    # Now, add groups to send notification message to
    for g in parent_message_groups:
        parent_message.groups.add(g)

    parent_message.save() # finally save once more

    if options:
        for option in options:
            option.pk = None
            option.child_msg = copy_tree(option.child_msg, composer)
            option.parent_msg = parent_message
            option.save()
    return parent_message


def collect_tree_content(parent_message):
    content = parent_message.get_full_content()

    options = parent_message.options.all()
    if options:
        for option in options:
            content += ' ' + collect_tree_content(option.child_msg)
    return content
