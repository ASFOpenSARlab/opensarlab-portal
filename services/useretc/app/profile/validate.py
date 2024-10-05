
class FormValidationException(Exception):
    """ Error in data validation """

def validate_form(form):
    
    for field in form:
        if form[field] == 'Choose...':
            print(f"There is a 'choose'. {field=} {form=}")
            #raise FormValidationException(f"Please choose an answer other than 'Choose...'")
