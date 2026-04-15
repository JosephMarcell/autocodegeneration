import { useNavigate } from 'react-router-dom';
import { useGlobalState, updateProcessState } from '../../../shared/state/globalState';
import { Card, Button } from '../../../shared/components/UI';

export const ChoosesWashPage = () => {
  const navigate = useNavigate();
  const { processState } = useGlobalState();

  const handleComplete = () => {
    updateProcessState({
      chooses_wash_completed: true,
      which_wash_program_result: "selected condition label"
    });
    navigate("/customer/pays-15");
  };

  return (
    <Card title="Chooses wash" hint="Page for BPMN task 'Chooses wash' (write-navigate).">
      <Button onClick={handleComplete}>Complete: Chooses Wash</Button>
    </Card>
  );
};