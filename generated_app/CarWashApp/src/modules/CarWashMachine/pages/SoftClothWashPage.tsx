import { useNavigate } from 'react-router-dom';
import { useGlobalState, updateProcessState } from '../../../shared/state/globalState';
import { Card, Button, Input } from '../../../shared/components/UI';

export const SoftClothWashPage = () => {
  const navigate = useNavigate();
  const { processState } = useGlobalState();

  const handleProceedClick = () => {
    updateProcessState({
      soft_cloth_wash_completed: true,
      which_wash_program_result: "selected condition label"
    });
    navigate("/car-wash-machine/wheel-clean");
  };

  return (
    <Card title="Soft Cloth Wash" hint="Page for BPMN task 'Soft Cloth Wash' (wait-then-write).">
      {processState.soft_cloth_wash_triggered ? (
        <Button onClick={handleProceedClick}>Proceed</Button>
      ) : (
        <div className="animate-spin text-gray-500">Waiting for soft cloth wash trigger...</div>
      )}
    </Card>
  );
};