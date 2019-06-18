from django.conf.urls import patterns, url
from campaigns.views import TaskQueueListView, CampaignConversationCreateView,\
    DeleteTaskQueueView, MultipleMessageConversationCreateView,\
    SingleMessageConversationCreateView, ConversationListView,\
    ConversationMessageTreeView, DeleteConversationView,\
    ConversationSendView, ConversationDuplicateView, ConversationTitleEditView, ListAllGroupsView, LinkableMessagesListView, \
    LinkMessageView, SetTutorialView


urlpatterns = patterns('',
    url(r'^create_single_msg/$', SingleMessageConversationCreateView.as_view(), name='create_single_msg_conv'),
    url(r'^create_conversation/$', MultipleMessageConversationCreateView.as_view(), name='create_multiple_msg_conv'),
    url(r'^link_message_list/$', LinkableMessagesListView.as_view(), name='link_message_list'),
    url(r'^link_messages/$', LinkMessageView.as_view(), name='link_messages'),

    url(r'^list/$', ConversationListView.as_view(), name='list'),

    # In the same order as these actions appear in conversation/list page
    url(r'^conversation_messages/$', ConversationMessageTreeView.as_view(), name='conversation_messages'),
    url(r'^send/$', ConversationSendView.as_view(), name='send'),
    url(r'^duplicate_conversation/$', ConversationDuplicateView.as_view(), name='duplicate_campaign'),
    url(r'^edit_conversation_title/(?P<pk>\d+)/$', ConversationTitleEditView.as_view(), name='edit_conversation_title'),
    url(r'^set_tutorial/$', SetTutorialView.as_view(), name='set_tutorial'),
    url(r'^delete_conversation/$', DeleteConversationView.as_view(), name='delete_conversation'),

    url(r'^taskq/$', TaskQueueListView.as_view(), name='taskq_list'),
    url(r'^delete_taskq/$', DeleteTaskQueueView.as_view(), name='delete_taskq'),

    url(r'^create/conversation/$', CampaignConversationCreateView.as_view(), name='create_conversation'),
    url(r'^list_all_groups/$', ListAllGroupsView.as_view(), name='list_all_groups'),
)
