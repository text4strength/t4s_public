'''
Created on Mar 21, 2014

@author: lacheephyo
'''
from smsmessages.models import MessageOption, Message
from smsmessages.constants import THANKYOU


class ConversationMixin(object):

    def create_single_message(self, form_data):
        msg = Message(content=form_data['parent_msg'], composer=self.request.user)
        msg.save()
        
        child_msg = Message(content=form_data['reply_msg'], composer=self.request.user)
        child_msg.save()
        
        msg_option = MessageOption(parent_msg=msg, child_msg=child_msg, trigger_keyword='*',
                                   option_content='')
        msg_option.save()
        return msg

    def process_options(self, option_json, parent_msg):
        option_ids = [];

        for option in option_json:
            # E.g., [{"id":"46","keyword":"ICECREAM","option_text":"TASTE SWEET '& http://amazon.com","reply":"YESSS"},{"keyword":"SOURCREAM","option_text":"TASTE SOUR (YEah)","reply":"NOOOOOO"}]
            # for newly created option rows, the id may be missing and we used option['id'], but
            # that failed to detect the missing 'id' key
            if option.get('id'):
                # update old option object
                option_obj = MessageOption.objects.get(id=option['id'])
                option_obj.child_msg.content = option['reply']
                option_obj.child_msg.save()
                
                option_obj.trigger_keyword = option['keyword'].strip()  # strips spaces if user happens to accidentally provide space around
                option_obj.option_content = option['option_text']
                option_obj.separator = option['separator']

                # Unfortunately, backgrid doesn't provide default values for its newly initialized cell values, so
                # we are not guaranteed to see this option key in some option objects. Therefore, set default as False here
                #option_obj.exclude_in_msg = option.get('exclude_option_text') or False
                if option.has_key('exclude_option_text'):
                    option_obj.exclude_in_msg = option.get('exclude_option_text')
                else:
                    option_obj.exclude_in_msg = option_obj.exclude_in_msg or False

                # do the same for 'notify' and 'wizard' as 'exclude_option_text'
                if option.has_key('notify'):
                    option_obj.notify = option.get('notify')
                else:
                    option_obj.notify = option_obj.notify or False

                if option.has_key('wizard'):
                    option_obj.wizard = option.get('wizard')
                else:
                    option_obj.wizard = option_obj.wizard or False

                option_obj.save()
                option_ids.append(option['id']) #add this to the list of options we want to keep/retain

            else:
                # create new option obj
                option_obj = MessageOption()
                
                child_msg = Message()
                child_msg.content = option['reply']
                child_msg.composer = self.request.user
                child_msg.save()
                
                option_obj.child_msg = child_msg
                
                option_obj.trigger_keyword = option['keyword']
                option_obj.option_content = option['option_text']
                option_obj.separator = option['separator']
                option_obj.parent_msg = parent_msg

                if option.has_key('exclude_option_text'):
                    option_obj.exclude_in_msg = option.get('exclude_option_text')
                else:
                    option_obj.exclude_in_msg = option_obj.exclude_in_msg or False

                # do the same for 'notify' and 'wizard' as 'exclude_option_text'
                if option.has_key('notify'):
                    option_obj.notify = option.get('notify')
                else:
                    option_obj.notify = option_obj.notify or False

                if option.has_key('wizard'):
                    option_obj.wizard = option.get('wizard')
                else:
                    option_obj.wizard = option_obj.wizard or False

                option_obj.save()
                option_ids.append(option_obj.id)    # make sure to add newly created option id

        # if user delete options, we need to delete it in DB
        parent_msg.options.exclude(id__in=option_ids).delete()
        
